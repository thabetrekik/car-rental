from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import ClientDocumentForm, OnlinePaymentForm, RegistrationForm, ReservationDetailsForm
from .models import (
    ACTIVE_RESERVATION_STATUSES,
    Client,
    DOCUMENT_CIN,
    DOCUMENT_DRIVING_LICENSE,
    Document,
    Payment,
    Reservation,
    RESERVATION_PENDING,
    User,
    Vehicle,
    sync_reservation_statuses,
)

def _is_admin_user(user):
    username = (getattr(user, "username", "") or "").strip().lower()
    role = (getattr(user, "role", "") or "").strip().lower()
    return bool(user and user.is_authenticated and (user.is_staff or role == "admin" or username == "admin"))


def _get_client_reservation_groups(client):
    sync_reservation_statuses()
    reservations = (
        Reservation.objects.filter(client=client)
        .select_related("vehicle")
        .order_by("-start_date", "-created_at")
    )
    active_reservations = reservations.filter(
        status__in=ACTIVE_RESERVATION_STATUSES,
    ).order_by("start_date", "created_at")
    reservation_history = reservations.exclude(
        id__in=active_reservations.values_list("id", flat=True)
    )
    return active_reservations, reservation_history


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=data["username"],
                        email=data["email"],
                        password=data["password"],
                        role="client",
                    )
                    Client.objects.create(
                        user=user,
                        last_name=data.get("last_name"),
                        first_name=data.get("first_name"),
                        email=data.get("email", ""),
                        phone=data.get("phone"),
                        birth_date=data.get("birth_date"),
                    )
                messages.success(request, "Account created successfully. Please log in.")
                return redirect("login")
            except Exception as exc:
                messages.error(request, f"An error occurred: {exc}")
        else:
            messages.error(request, "Please check the highlighted fields and try again.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        if _is_admin_user(request.user):
            return redirect("dashboard")
        return redirect("index")

    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")
        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome {user.username}!")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            if _is_admin_user(user):
                return redirect("dashboard")
            return redirect("index")
        messages.error(request, "Incorrect username or password.")
    return render(request, "accounts/login.html")


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


def index(request):
    client_profile = None
    today = timezone.localdate()
    if request.user.is_authenticated:
        client_profile = Client.objects.filter(user=request.user).first()
        if client_profile:
            sync_reservation_statuses()

    context = {
        "client_profile": client_profile,
        "category_choices": Vehicle.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category"),
        "today_date": today.isoformat(),
    }
    return render(request, "index.html", context)


def workflow_page(request):
    return render(request, "workflow.html")


def cars_page(request):
    query = (request.GET.get("q") or "").strip()
    selected_category = (request.GET.get("category") or "").strip()
    selected_fuel = (request.GET.get("fuel") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()

    vehicles = Vehicle.objects.order_by("-id")

    if query:
        vehicles = vehicles.filter(
            Q(brand__icontains=query)
            | Q(model__icontains=query)
            | Q(category__icontains=query)
            | Q(fuel_type__icontains=query)
            | Q(description__icontains=query)
        )

    if selected_category:
        vehicles = vehicles.filter(category__iexact=selected_category)

    if selected_fuel:
        vehicles = vehicles.filter(fuel_type__iexact=selected_fuel)

    if selected_status:
        vehicles = vehicles.filter(status__iexact=selected_status)

    context = {
        "vehicles": vehicles,
        "query": query,
        "selected_category": selected_category,
        "selected_fuel": selected_fuel,
        "selected_status": selected_status,
        "category_choices": Vehicle.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category"),
        "fuel_choices": Vehicle.objects.exclude(fuel_type="")
        .values_list("fuel_type", flat=True)
        .distinct()
        .order_by("fuel_type"),
        "status_choices": Vehicle.objects.exclude(status="")
        .values_list("status", flat=True)
        .distinct()
        .order_by("status"),
    }
    return render(request, "cars.html", context)


def car_details_page(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    return render(request, "car_details.html", {"vehicle": vehicle})


def reservation_history_page(request):
    if not request.user.is_authenticated:
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.path}")

    client = Client.objects.filter(user=request.user).first()
    if not client:
        messages.error(request, "Your account does not have a client profile yet.")
        return redirect("index")

    active_reservations, reservation_history = _get_client_reservation_groups(client)
    context = {
        "client_profile": client,
        "active_reservations": active_reservations,
        "reservation_history": reservation_history,
    }
    return render(request, "reservation_history.html", context)


def reservation_page(request, vehicle_id):
    if not request.user.is_authenticated:
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.path}")

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    client = Client.objects.filter(user=request.user).first()

    if not client:
        messages.error(request, "Your account does not have a client profile yet.")
        return redirect("cars")

    today_iso = timezone.localdate().isoformat()

    if request.method == "POST":
        form = ReservationDetailsForm(request.POST, daily_price=vehicle.daily_price)
        form.fields["start_date"].widget.attrs["min"] = today_iso
        form.fields["end_date"].widget.attrs["min"] = today_iso

        if form.is_valid():
            reservation = Reservation.objects.create(
                client=client,
                vehicle=vehicle,
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
                total_price=form.cleaned_data["total_price"],
                payment_status="pending",
                number_of_days=form.cleaned_data["number_of_days"],
                status=RESERVATION_PENDING,
            )
            if form.cleaned_data["payment_method"] == ReservationDetailsForm.PAYMENT_METHOD_ONLINE:
                messages.success(request, "Reservation request saved. Complete the online payment to mark it as paid.")
                return redirect("online_payment", reservation_id=reservation.id)
            messages.success(request, "Reservation request sent successfully. Payment stays pending until it is recorded.")
            reservation_url = reverse("reservation", args=[vehicle.id])
            return redirect(f"{reservation_url}?created={reservation.id}")
    else:
        form = ReservationDetailsForm(daily_price=vehicle.daily_price)
        form.fields["start_date"].widget.attrs["min"] = today_iso
        form.fields["end_date"].widget.attrs["min"] = today_iso

    created_reservation = None
    created_reservation_id = request.GET.get("created")
    if created_reservation_id and created_reservation_id.isdigit():
        created_reservation = Reservation.objects.filter(
            id=created_reservation_id,
            client=client,
            vehicle=vehicle,
        ).first()

    context = {
        "vehicle": vehicle,
        "form": form,
        "created_reservation": created_reservation,
    }
    return render(request, "reservation_details.html", context)


def online_payment_page(request, reservation_id):
    if not request.user.is_authenticated:
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.path}")

    client = Client.objects.filter(user=request.user).first()
    if not client:
        messages.error(request, "Your account does not have a client profile yet.")
        return redirect("index")

    reservation = get_object_or_404(
        Reservation.objects.select_related("vehicle", "client"),
        pk=reservation_id,
        client=client,
    )

    if reservation.is_paid:
        messages.info(request, "This reservation is already paid.")
        return redirect("reservation_history")

    initial = {
        "card_holder": f"{client.first_name} {client.last_name}".strip(),
        "expiry_year": timezone.localdate().year,
    }
    form = OnlinePaymentForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        reference = f"ONLINE-{reservation.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        Payment.objects.update_or_create(
            reservation=reservation,
            defaults={
                "amount": reservation.total_price,
                "method": "online",
                "reference": reference,
            },
        )
        messages.success(request, "Online payment completed. Your reservation is now marked as paid.")
        return redirect("reservation_history")

    return render(request, "online_payment.html", {"form": form, "reservation": reservation})


def client_documents_page(request):
    if not request.user.is_authenticated:
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.path}")

    client = Client.objects.filter(user=request.user).first()
    if not client:
        messages.error(request, "Your account does not have a client profile yet.")
        return redirect("index")

    form = ClientDocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        cin_file = form.cleaned_data.get("cin_file")
        driving_license_file = form.cleaned_data.get("driving_license_file")

        if cin_file:
            Document.objects.create(client=client, document_type=DOCUMENT_CIN, file=cin_file)
        if driving_license_file:
            Document.objects.create(client=client, document_type=DOCUMENT_DRIVING_LICENSE, file=driving_license_file)

        messages.success(request, "Documents uploaded successfully.")
        return redirect("client_documents")

    documents = Document.objects.filter(client=client).order_by("-uploaded_at", "-id")
    return render(
        request,
        "client_documents.html",
        {
            "form": form,
            "documents": documents,
            "client_profile": client,
        },
    )
