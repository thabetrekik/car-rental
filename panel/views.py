from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Sum
from django.db.models.deletion import RestrictedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import (
    Client,
    DEPOSIT_CASHED,
    DEPOSIT_PENDING,
    DEPOSIT_RETURNED,
    DEPOSIT_STATUS_CHOICES,
    Deposit,
    Document,
    Expense,
    FIXED_CHARGE_COMPLETED,
    FIXED_CHARGE_PENDING,
    FIXED_CHARGE_STATUS_CHOICES,
    FixedChargeAlert,
    Maintenance,
    Payment,
    Reservation,
    RESERVATION_STATUS_CHOICES,
    User,
    Vehicle,
    sync_reservation_statuses,
)
from .forms import ClientCreateForm, ClientUpdateForm, DepositForm, ExpenseForm, FixedChargeAlertForm, MaintenanceForm, VehicleForm


def _is_admin(user):
    username = (getattr(user, "username", "") or "").strip().lower()
    role = (getattr(user, "role", "") or "").strip().lower()
    return bool(user and user.is_authenticated and (user.is_staff or role == "admin" or username == "admin"))


FINANCE_EXPENSE_CATEGORIES = [
    "Oil Change",
    "Fuel",
    "Leasing",
    "Spare Parts",
    "Other",
]

FIXED_CHARGE_ALERT_WINDOW_DAYS = 7


def _expense_category_label(maintenance_type):
    text = (maintenance_type or "").strip().lower()

    if any(keyword in text for keyword in ["vidange", "huile", "oil"]):
        return "Oil Change"
    if any(keyword in text for keyword in ["essence", "carburant", "fuel", "diesel", "gasoil"]):
        return "Fuel"
    if any(keyword in text for keyword in ["leasing", "lease"]):
        return "Leasing"
    if any(keyword in text for keyword in ["piece", "pieces", "pièce", "pièces", "spare"]):
        return "Spare Parts"
    return "Other"


def _build_finance_summary():
    today = timezone.localdate()
    start_week = today - timedelta(days=today.weekday())
    start_month = today.replace(day=1)
    periods = [
        ("Day", today, today),
        ("Week", start_week, today),
        ("Month", start_month, today),
    ]

    paid_reservations = Reservation.objects.filter(payment_status__iexact="paid").exclude(status__iexact="cancelled")
    summaries = []

    for label, start_date, end_date in periods:
        maintenance_expenses = list(
            Maintenance.objects.filter(date__range=(start_date, end_date)).only("cost", "maintenance_type")
        )
        manual_expenses = list(
            Expense.objects.filter(date__range=(start_date, end_date)).only("amount", "category")
        )

        breakdown_map = {category: Decimal("0.00") for category in FINANCE_EXPENSE_CATEGORIES}
        for expense in maintenance_expenses:
            breakdown_map[_expense_category_label(expense.maintenance_type)] += expense.cost or Decimal("0.00")
        for expense in manual_expenses:
            breakdown_map[expense.category] = breakdown_map.get(expense.category, Decimal("0.00")) + (expense.amount or Decimal("0.00"))

        income = (
            paid_reservations.filter(created_at__date__range=(start_date, end_date)).aggregate(total=Sum("total_price"))["total"]
            or Decimal("0.00")
        )
        expenses_total = sum(breakdown_map.values(), Decimal("0.00"))

        summaries.append(
            {
                "label": label,
                "range_label": start_date.strftime("%d/%m/%Y") if start_date == end_date else f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                "income": income,
                "expenses": expenses_total,
                "net": income - expenses_total,
                "expense_breakdown": [
                    {"label": category, "amount": amount}
                    for category, amount in breakdown_map.items()
                ],
            }
        )

    return summaries


def _build_vehicle_roi_summary():
    income_rows = (
        Reservation.objects.filter(payment_status__iexact="paid")
        .exclude(status__iexact="cancelled")
        .values("vehicle_id")
        .annotate(total_income=Sum("total_price"))
    )
    maintenance_expense_rows = (
        Maintenance.objects.values("vehicle_id")
        .annotate(total_expenses=Sum("cost"))
    )
    manual_expense_rows = (
        Expense.objects.exclude(vehicle_id__isnull=True)
        .values("vehicle_id")
        .annotate(total_expenses=Sum("amount"))
    )

    income_map = {row["vehicle_id"]: row["total_income"] or Decimal("0.00") for row in income_rows}
    expense_map = {row["vehicle_id"]: row["total_expenses"] or Decimal("0.00") for row in maintenance_expense_rows}

    for row in manual_expense_rows:
        vehicle_id = row["vehicle_id"]
        expense_map[vehicle_id] = expense_map.get(vehicle_id, Decimal("0.00")) + (row["total_expenses"] or Decimal("0.00"))

    vehicles = Vehicle.objects.order_by("brand", "model", "id")
    roi_summary = []

    for vehicle in vehicles:
        total_income = income_map.get(vehicle.id, Decimal("0.00"))
        total_expenses = expense_map.get(vehicle.id, Decimal("0.00"))
        net_result = total_income - total_expenses

        if net_result > 0:
            performance = "Profitable"
            performance_class = "roi-badge--positive"
        elif net_result < 0:
            performance = "Loss-making"
            performance_class = "roi-badge--negative"
        else:
            performance = "Break-even"
            performance_class = "roi-badge--neutral"

        roi_summary.append(
            {
                "vehicle": vehicle,
                "reference": f"Vehicle #{vehicle.id}",
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_result": net_result,
                "performance": performance,
                "performance_class": performance_class,
            }
        )

    roi_summary.sort(key=lambda item: item["net_result"], reverse=True)
    return roi_summary


def _build_deposit_summary():
    summary = []
    for value, label in DEPOSIT_STATUS_CHOICES:
        deposits = Deposit.objects.filter(status=value)
        total_amount = deposits.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        summary.append(
            {
                "value": value,
                "label": label,
                "count": deposits.count(),
                "amount": total_amount,
            }
        )
    return summary


def _get_fixed_charge_alert_meta(alert, today=None):
    today = today or timezone.localdate()

    if alert.status == FIXED_CHARGE_COMPLETED:
        return {
            "code": "completed",
            "label": "Completed",
            "badge_class": "status-badge--returned",
            "due_text": f"Completed on {alert.completed_at}" if alert.completed_at else "Completed",
        }

    days_remaining = (alert.due_date - today).days
    if days_remaining < 0:
        return {
            "code": "overdue",
            "label": "Overdue",
            "badge_class": "status-badge--cashed",
            "due_text": f"Overdue by {abs(days_remaining)} day(s)",
        }
    if days_remaining <= FIXED_CHARGE_ALERT_WINDOW_DAYS:
        return {
            "code": "due_soon",
            "label": "Due soon",
            "badge_class": "status-badge--pending",
            "due_text": "Due today" if days_remaining == 0 else f"Due in {days_remaining} day(s)",
        }
    return {
        "code": "upcoming",
        "label": "Upcoming",
        "badge_class": "status-badge--info",
        "due_text": f"Due in {days_remaining} day(s)",
    }


def _serialize_fixed_charge_alert(alert, today=None):
    today = today or timezone.localdate()
    meta = _get_fixed_charge_alert_meta(alert, today)
    vehicle_name = f"{alert.vehicle.brand} {alert.vehicle.model}" if alert.vehicle_id else "General"
    amount = alert.amount or Decimal("0.00")

    return {
        "id": alert.id,
        "vehicle_name": vehicle_name,
        "category_label": alert.get_category_display(),
        "due_date": alert.due_date.strftime("%Y-%m-%d"),
        "amount": amount,
        "notes": alert.notes,
        "status": alert.status,
        "status_label": meta["label"],
        "status_class": meta["badge_class"],
        "due_text": meta["due_text"],
        "alert_key": f"{alert.id}:{meta['code']}",
        "notification_text": f"{alert.get_category_display()} for {vehicle_name} - {meta['due_text']}",
    }


def _build_fixed_charge_alert_summary():
    today = timezone.localdate()
    due_limit = today + timedelta(days=FIXED_CHARGE_ALERT_WINDOW_DAYS)

    overdue = FixedChargeAlert.objects.filter(status=FIXED_CHARGE_PENDING, due_date__lt=today)
    due_soon = FixedChargeAlert.objects.filter(status=FIXED_CHARGE_PENDING, due_date__gte=today, due_date__lte=due_limit)
    completed = FixedChargeAlert.objects.filter(status=FIXED_CHARGE_COMPLETED)

    return [
        {
            "label": "Overdue",
            "count": overdue.count(),
            "amount": overdue.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "status_class": "status-badge--cashed",
        },
        {
            "label": "Due soon",
            "count": due_soon.count(),
            "amount": due_soon.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "status_class": "status-badge--pending",
        },
        {
            "label": "Completed",
            "count": completed.count(),
            "amount": completed.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "status_class": "status-badge--returned",
        },
    ]


def _build_fixed_charge_alert_items():
    today = timezone.localdate()
    alerts = FixedChargeAlert.objects.select_related("vehicle").order_by("status", "due_date", "id")
    return [_serialize_fixed_charge_alert(alert, today) for alert in alerts]


def _build_notification_fixed_charge_alerts():
    today = timezone.localdate()
    due_limit = today + timedelta(days=FIXED_CHARGE_ALERT_WINDOW_DAYS)
    alerts = (
        FixedChargeAlert.objects.filter(status=FIXED_CHARGE_PENDING, due_date__lte=due_limit)
        .select_related("vehicle")
        .order_by("due_date", "id")
    )
    return [_serialize_fixed_charge_alert(alert, today) for alert in alerts]


def _build_dashboard_context(request):
    client_form = ClientCreateForm(prefix="client")
    vehicle_form = VehicleForm(prefix="vehicle")
    maintenance_form = MaintenanceForm(prefix="maintenance")
    response = None
    active_tab = request.GET.get("tab") or "client-form"
    if active_tab not in {"client-form", "vehicle-form", "maintenance-form"}:
        active_tab = "client-form"

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "client":
            active_tab = "client-form"
            client_form = ClientCreateForm(request.POST, prefix="client")
            if client_form.is_valid():
                try:
                    with transaction.atomic():
                        client_form.save()
                    messages.success(request, "Client added successfully.")
                    response = redirect("dashboard")
                except Exception as exc:
                    messages.error(request, f"Error adding client: {exc}")
            else:
                messages.error(request, "Please fix the client form errors.")

        elif form_type == "vehicle":
            active_tab = "vehicle-form"
            vehicle_form = VehicleForm(request.POST, request.FILES, prefix="vehicle")
            if vehicle_form.is_valid():
                try:
                    vehicle_form.save()
                    messages.success(request, "Vehicle added successfully.")
                    response = redirect("dashboard")
                except Exception as exc:
                    messages.error(request, f"Error adding vehicle: {exc}")
            else:
                messages.error(request, "Please fix the vehicle form errors.")
        elif form_type == "maintenance":
            active_tab = "maintenance-form"
            maintenance_form = MaintenanceForm(request.POST, prefix="maintenance")
            if maintenance_form.is_valid():
                try:
                    with transaction.atomic():
                        maintenance = maintenance_form.save()
                        maintenance.vehicle.status = maintenance.status
                        maintenance.vehicle.save(update_fields=["status"])
                    messages.success(request, "Maintenance added and vehicle status updated.")
                    response = redirect("dashboard")
                except Exception as exc:
                    messages.error(request, f"Error adding maintenance: {exc}")
            else:
                messages.error(request, "Please fix the maintenance form errors.")
        else:
            messages.error(request, "Invalid form type.")

    return response, {
        "client_form": client_form,
        "vehicle_form": vehicle_form,
        "maintenance_form": maintenance_form,
        "active_tab": active_tab,
        "total_clients": Client.objects.count(),
        "total_vehicles": Vehicle.objects.count(),
        "total_reservations": Reservation.objects.count(),
        "total_maintenances": Maintenance.objects.count(),
        "total_users": User.objects.count(),
        "finance_summary": _build_finance_summary(),
    }


@login_required
def admin_panel(request):
    if not _is_admin(request.user):
        return redirect("login")
    response, context = _build_dashboard_context(request)
    if response:
        return response
    return render(request, "panel/dashboard.html", context)


@login_required
def dashboard(request):
    if not _is_admin(request.user):
        return redirect("login")
    response, context = _build_dashboard_context(request)
    if response:
        return response
    return render(request, "panel/dashboard.html", context)



@login_required
def finance_page(request):
    if not _is_admin(request.user):
        return redirect("login")

    expense_form = ExpenseForm(prefix="expense")
    deposit_form = DepositForm(prefix="deposit")
    fixed_charge_form = FixedChargeAlertForm(prefix="fixed_charge")

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "expense":
            expense_form = ExpenseForm(request.POST, prefix="expense")
            if expense_form.is_valid():
                expense_form.save()
                messages.success(request, "Expense added successfully.")
                return redirect("finance_page")
            messages.error(request, "Please fix the expense form errors.")

        elif form_type == "deposit":
            deposit_form = DepositForm(request.POST, prefix="deposit")
            if deposit_form.is_valid():
                deposit = deposit_form.save(commit=False)
                if deposit.status in {DEPOSIT_RETURNED, DEPOSIT_CASHED} and not deposit.resolved_at:
                    deposit.resolved_at = deposit.received_at
                deposit.save()
                messages.success(request, "Guarantee added successfully.")
                return redirect("finance_page")
            messages.error(request, "Please fix the guarantee form errors.")

        elif form_type == "deposit_status":
            deposit = get_object_or_404(Deposit, pk=request.POST.get("deposit_id"))
            new_status = request.POST.get("status")

            if new_status not in {choice[0] for choice in DEPOSIT_STATUS_CHOICES}:
                messages.error(request, "Invalid guarantee status.")
            else:
                deposit.status = new_status
                deposit.resolved_at = timezone.localdate() if new_status in {DEPOSIT_RETURNED, DEPOSIT_CASHED} else None
                deposit.save(update_fields=["status", "resolved_at"])
                messages.success(request, "Guarantee status updated.")
                return redirect("finance_page")

        elif form_type == "fixed_charge":
            fixed_charge_form = FixedChargeAlertForm(request.POST, prefix="fixed_charge")
            if fixed_charge_form.is_valid():
                fixed_charge_form.save()
                messages.success(request, "Fixed charge alert added successfully.")
                return redirect("finance_page")
            messages.error(request, "Please fix the fixed charge form errors.")

        elif form_type == "fixed_charge_status":
            alert = get_object_or_404(FixedChargeAlert, pk=request.POST.get("alert_id"))
            new_status = (request.POST.get("status") or "").strip().lower()

            if new_status not in {choice[0] for choice in FIXED_CHARGE_STATUS_CHOICES}:
                messages.error(request, "Invalid fixed charge status.")
            else:
                alert.status = new_status
                alert.completed_at = timezone.localdate() if new_status == FIXED_CHARGE_COMPLETED else None
                alert.save(update_fields=["status", "completed_at"])
                messages.success(request, "Fixed charge alert updated.")
                return redirect("finance_page")

        else:
            messages.error(request, "Invalid finance action.")

    context = {
        "expense_form": expense_form,
        "deposit_form": deposit_form,
        "fixed_charge_form": fixed_charge_form,
        "deposit_status_choices": DEPOSIT_STATUS_CHOICES,
        "fixed_charge_status_choices": FIXED_CHARGE_STATUS_CHOICES,
        "deposit_summary": _build_deposit_summary(),
        "deposits": Deposit.objects.select_related("reservation__client", "reservation__vehicle").order_by("-received_at", "-id"),
        "fixed_charge_summary": _build_fixed_charge_alert_summary(),
        "fixed_charge_alerts": _build_fixed_charge_alert_items(),
        "finance_summary": _build_finance_summary(),
        "vehicle_roi_summary": _build_vehicle_roi_summary(),
    }
    return render(request, "panel/finance_page.html", context)



@login_required
def reservation_notifications(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    sync_reservation_statuses()

    try:
        since_id = int(request.GET.get("since_id", "0"))
    except (TypeError, ValueError):
        since_id = 0

    latest_id = Reservation.objects.order_by("-id").values_list("id", flat=True).first() or 0
    pending_reservations = (
        Reservation.objects.filter(status__iexact="pending")
        .select_related("client", "vehicle")
        .order_by("-created_at", "-id")
    )
    new_reservations = (
        Reservation.objects.filter(id__gt=since_id, status__iexact="pending")
        .select_related("client", "vehicle")
        .order_by("id")
    )

    def serialize(reservation):
        return {
            "id": reservation.id,
            "client_name": f"{reservation.client.first_name} {reservation.client.last_name}".strip(),
            "vehicle_name": f"{reservation.vehicle.brand} {reservation.vehicle.model}".strip(),
            "start_date": reservation.start_date.strftime("%Y-%m-%d"),
            "end_date": reservation.end_date.strftime("%Y-%m-%d"),
            "created_at": timezone.localtime(reservation.created_at).strftime("%Y-%m-%d %H:%M"),
        }

    fixed_charge_alerts = _build_notification_fixed_charge_alerts()

    return JsonResponse(
        {
            "latest_id": latest_id,
            "pending_count": pending_reservations.count(),
            "new_reservations": [serialize(reservation) for reservation in new_reservations],
            "recent_pending": [serialize(reservation) for reservation in pending_reservations[:5]],
            "fixed_charge_count": len(fixed_charge_alerts),
            "fixed_charge_alerts": [
                {
                    **alert,
                    "amount": str(alert["amount"]),
                    "amount_display": f"${alert['amount']:.2f}",
                }
                for alert in fixed_charge_alerts
            ],
            "total_count": pending_reservations.count() + len(fixed_charge_alerts),
        }
    )


@login_required
def client_page(request):
    if not _is_admin(request.user):
        return redirect("login")

    client_form = ClientCreateForm()
    clients = (
        Client.objects.select_related("user")
        .prefetch_related(
            Prefetch(
                "document_set",
                queryset=Document.objects.order_by("-uploaded_at", "-id"),
                to_attr="uploaded_documents",
            )
        )
        .order_by("-id")
    )
    if request.method == "POST":
        client_form = ClientCreateForm(request.POST)
        if client_form.is_valid():
            try:
                with transaction.atomic():
                    client_form.save()
                messages.success(request, "Client added successfully.")
                return redirect("client_page")
            except Exception as exc:
                messages.error(request, f"Error adding client: {exc}")
        else:
            messages.error(request, "Please fix the client form errors.")

    context = {"client_form": client_form, "clients": clients}
    return render(request, "panel/client_page.html", context)


@login_required
def vehicle_page(request):
    if not _is_admin(request.user):
        return redirect("login")

    vehicle_form = VehicleForm()
    vehicles = Vehicle.objects.annotate(reservation_count=Count("reservation")).order_by("-id")
    if request.method == "POST":
        vehicle_form = VehicleForm(request.POST, request.FILES)
        if vehicle_form.is_valid():
            try:
                vehicle_form.save()
                messages.success(request, "Vehicle added successfully.")
                return redirect("vehicle_page")
            except Exception as exc:
                messages.error(request, f"Error adding vehicle: {exc}")
        else:
            messages.error(request, "Please fix the vehicle form errors.")

    context = {"vehicle_form": vehicle_form, "vehicles": vehicles}
    return render(request, "panel/vehicle_page.html", context)


@login_required
def maintenance_page(request):
    if not _is_admin(request.user):
        return redirect("login")

    maintenance_form = MaintenanceForm()
    maintenances = Maintenance.objects.select_related("vehicle").order_by("-date", "-id")
    if request.method == "POST":
        maintenance_form = MaintenanceForm(request.POST)
        if maintenance_form.is_valid():
            try:
                with transaction.atomic():
                    maintenance = maintenance_form.save()
                    maintenance.vehicle.status = maintenance.status
                    maintenance.vehicle.save(update_fields=["status"])
                messages.success(request, "Maintenance added and vehicle status updated.")
                return redirect("maintenance_page")
            except Exception as exc:
                messages.error(request, f"Error adding maintenance: {exc}")
        else:
            messages.error(request, "Please fix the maintenance form errors.")

    context = {"maintenance_form": maintenance_form, "maintenances": maintenances}
    return render(request, "panel/maintenance_page.html", context)


@login_required
def reservation_page(request):
    if not _is_admin(request.user):
        return redirect("login")

    sync_reservation_statuses()

    allowed_payment_statuses = {"pending", "paid", "failed"}
    allowed_statuses = {value for value, _ in RESERVATION_STATUS_CHOICES}

    if request.method == "POST":
        reservation_id = request.POST.get("reservation_id")
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        payment_status = (request.POST.get("payment_status") or "").strip().lower()
        status = (request.POST.get("status") or "").strip().lower()

        if payment_status not in allowed_payment_statuses or status not in allowed_statuses:
            messages.error(request, "Invalid reservation status values.")
        else:
            reservation.payment_status = payment_status
            reservation.status = status
            reservation.save(update_fields=["payment_status", "status"])

            if payment_status == "paid":
                Payment.objects.update_or_create(
                    reservation=reservation,
                    defaults={
                        "amount": reservation.total_price,
                        "method": "admin_recorded",
                        "reference": f"PAY-{reservation.id}",
                    },
                )
            else:
                Payment.objects.filter(reservation=reservation).delete()

            sync_reservation_statuses()
            messages.success(request, "Reservation updated successfully.")
        return redirect("reservation_page")

    reservations = Reservation.objects.select_related(
        "client",
        "client__user",
        "vehicle",
    ).order_by("-created_at", "-id")
    context = {
        "reservations": reservations,
        "payment_choices": [("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed")],
        "status_choices": RESERVATION_STATUS_CHOICES,
    }
    return render(request, "panel/reservation_page.html", context)


@login_required
def client_edit(request, client_id):
    if not _is_admin(request.user):
        return redirect("login")

    client = get_object_or_404(Client.objects.select_related("user"), pk=client_id)
    client_form = ClientUpdateForm(instance=client)
    client_documents = Document.objects.filter(client=client).order_by("-uploaded_at", "-id")

    if request.method == "POST":
        client_form = ClientUpdateForm(request.POST, instance=client)
        if client_form.is_valid():
            try:
                with transaction.atomic():
                    client_form.save()
                messages.success(request, "Client updated successfully.")
                return redirect("client_page")
            except Exception as exc:
                messages.error(request, f"Error updating client: {exc}")
        else:
            messages.error(request, "Please fix the client form errors.")

    context = {"client_form": client_form, "client": client, "client_documents": client_documents}
    return render(request, "panel/client_edit.html", context)


@login_required
@require_POST
def client_delete(request, client_id):
    if not _is_admin(request.user):
        return redirect("login")

    client = get_object_or_404(Client, pk=client_id)
    try:
        client.user.delete()
        messages.success(request, "Client deleted successfully.")
    except Exception as exc:
        messages.error(request, f"Error deleting client: {exc}")

    return redirect("client_page")


@login_required
def vehicle_edit(request, vehicle_id):
    if not _is_admin(request.user):
        return redirect("login")

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    vehicle_form = VehicleForm(instance=vehicle)

    if request.method == "POST":
        vehicle_form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if vehicle_form.is_valid():
            try:
                vehicle_form.save()
                messages.success(request, "Vehicle updated successfully.")
                return redirect("vehicle_page")
            except Exception as exc:
                messages.error(request, f"Error updating vehicle: {exc}")
        else:
            messages.error(request, "Please fix the vehicle form errors.")

    context = {"vehicle_form": vehicle_form, "vehicle": vehicle}
    return render(request, "panel/vehicle_edit.html", context)


@login_required
@require_POST
def vehicle_delete(request, vehicle_id):
    if not _is_admin(request.user):
        return redirect("login")

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    reservation_count = Reservation.objects.filter(vehicle=vehicle).count()
    try:
        vehicle.delete()
        messages.success(request, "Vehicle deleted successfully.")
    except RestrictedError:
        messages.error(
            request,
            f"Cannot delete {vehicle.brand} {vehicle.model} because it is linked to {reservation_count} reservation(s). Delete those reservations first.",
        )
    except Exception as exc:
        messages.error(request, f"Error deleting vehicle: {exc}")

    return redirect("vehicle_page")


@login_required
@require_POST
def maintenance_delete(request, maintenance_id):
    if not _is_admin(request.user):
        return redirect("login")

    maintenance = get_object_or_404(Maintenance, pk=maintenance_id)
    try:
        maintenance.delete()
        messages.success(request, "Maintenance deleted successfully.")
    except Exception as exc:
        messages.error(request, f"Error deleting maintenance: {exc}")

    return redirect("maintenance_page")


@login_required
@require_POST
def reservation_delete(request, reservation_id):
    if not _is_admin(request.user):
        return redirect("login")

    reservation = get_object_or_404(Reservation, pk=reservation_id)
    try:
        reservation.delete()
        messages.success(request, "Reservation deleted successfully.")
    except Exception as exc:
        messages.error(request, f"Error deleting reservation: {exc}")

    return redirect("reservation_page")

