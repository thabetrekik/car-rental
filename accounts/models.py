from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

RESERVATION_PENDING = "pending"
RESERVATION_ACCEPTED = "accepted"
RESERVATION_CANCELLED = "cancelled"
RESERVATION_ENDED = "ended"

RESERVATION_STATUS_CHOICES = [
    (RESERVATION_PENDING, "Pending"),
    (RESERVATION_ACCEPTED, "Accepted"),
    (RESERVATION_CANCELLED, "Cancelled"),
    (RESERVATION_ENDED, "Ended"),
]

ACTIVE_RESERVATION_STATUSES = [RESERVATION_PENDING, RESERVATION_ACCEPTED]

EXPENSE_CATEGORY_CHOICES = [
    ("Oil Change", "Oil Change"),
    ("Fuel", "Fuel"),
    ("Leasing", "Leasing"),
    ("Spare Parts", "Spare Parts"),
    ("Other", "Other"),
]

DEPOSIT_METHOD_CHOICES = [
    ("check", "Check"),
    ("cash", "Cash"),
    ("card_hold", "Card hold"),
]

DEPOSIT_PENDING = "pending"
DEPOSIT_RETURNED = "returned"
DEPOSIT_CASHED = "cashed"

DEPOSIT_STATUS_CHOICES = [
    (DEPOSIT_PENDING, "Pending"),
    (DEPOSIT_RETURNED, "Returned"),
    (DEPOSIT_CASHED, "Cashed"),
]

FIXED_CHARGE_CATEGORY_CHOICES = [
    ("insurance", "Insurance"),
    ("technical_inspection", "Technical Inspection"),
    ("vignette", "Vignette"),
    ("bank_installment", "Bank Installment"),
]

FIXED_CHARGE_PENDING = "pending"
FIXED_CHARGE_COMPLETED = "completed"

FIXED_CHARGE_STATUS_CHOICES = [
    (FIXED_CHARGE_PENDING, "Pending"),
    (FIXED_CHARGE_COMPLETED, "Completed"),
]

DOCUMENT_CIN = "cin"
DOCUMENT_DRIVING_LICENSE = "driving_license"

DOCUMENT_TYPE_CHOICES = [
    (DOCUMENT_CIN, "CIN"),
    (DOCUMENT_DRIVING_LICENSE, "Driving Licence"),
]


class User(AbstractUser):
    role = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username


class Client(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_name = models.CharField(max_length=100, db_column="nom")
    first_name = models.CharField(max_length=100, db_column="prenom")
    email = models.CharField(max_length=150)
    password = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, db_column="telephone")
    birth_date = models.DateField(null=True, blank=True, db_column="date_naissance")

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Vehicle(models.Model):
    brand = models.CharField(max_length=100, db_column="marque")
    model = models.CharField(max_length=100, db_column="modele")
    year = models.IntegerField(db_column="annee")
    daily_price = models.DecimalField(max_digits=10, decimal_places=2, db_column="prix_par_jour")
    status = models.CharField(max_length=50, db_column="statut")
    fuel_type = models.CharField(max_length=50, db_column="carburantType")
    mileage = models.IntegerField(db_column="kilometrage")
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, db_column="categorie")
    photo = models.ImageField(upload_to="vehicles/", blank=True, null=True)

    def __str__(self):
        return f"{self.brand} {self.model}"


class Reservation(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.RESTRICT)
    start_date = models.DateField(db_column="date_debut")
    end_date = models.DateField(db_column="date_fin")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, db_column="prix_total")
    payment_status = models.CharField(max_length=50, db_column="Etat_paiement")
    created_at = models.DateTimeField(auto_now_add=True, db_column="date_creation")
    number_of_days = models.IntegerField(db_column="nombre_jour")
    status = models.CharField(max_length=50, db_column="statut")

    class Meta:
        db_table = "reservation"

    @property
    def is_paid(self):
        return (self.payment_status or "").strip().lower() == "paid"


def sync_reservation_statuses():
    Reservation.objects.filter(status__iexact="confirmed").update(status=RESERVATION_ACCEPTED)
    Reservation.objects.filter(status__iexact="completed").update(status=RESERVATION_ENDED)


class Payment(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_column="montant")
    method = models.CharField(max_length=50, db_column="methode")
    payment_date = models.DateTimeField(auto_now_add=True, db_column="date_paiement")
    reference = models.CharField(max_length=100)

    class Meta:
        db_table = "accounts_paiement"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Reservation.objects.filter(pk=self.reservation_id).exclude(payment_status__iexact="paid").update(payment_status="paid")


class Maintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    date = models.DateField()
    maintenance_type = models.CharField(max_length=100, db_column="type")
    cost = models.DecimalField(max_digits=10, decimal_places=2, db_column="cout")
    description = models.TextField()
    status = models.CharField(max_length=50, db_column="statut")

    class Meta:
        db_table = "maintenance"


class Expense(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    category = models.CharField(max_length=50, choices=EXPENSE_CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        db_table = "expense"


class Deposit(models.Model):
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="deposit",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=DEPOSIT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=DEPOSIT_STATUS_CHOICES, default=DEPOSIT_PENDING)
    received_at = models.DateField(default=timezone.localdate)
    resolved_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "deposit"


class FixedChargeAlert(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fixed_charge_alerts",
    )
    category = models.CharField(max_length=40, choices=FIXED_CHARGE_CATEGORY_CHOICES)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=FIXED_CHARGE_STATUS_CHOICES, default=FIXED_CHARGE_PENDING)
    completed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "fixed_charge_alert"


class Document(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES, default=DOCUMENT_CIN)
    file = models.FileField(upload_to="documents/", db_column="fichier")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_column="date_upload")

    def __str__(self):
        return f"{self.client} - {self.get_document_type_display()}"
