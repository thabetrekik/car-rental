from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import Client, Deposit, Expense, FixedChargeAlert, Maintenance, Reservation, Vehicle

User = get_user_model()


class ReservationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        client_name = f"{obj.client.first_name} {obj.client.last_name}".strip()
        vehicle_name = f"{obj.vehicle.brand} {obj.vehicle.model}".strip()
        return f"#{obj.id} - {client_name} - {vehicle_name} ({obj.start_date} to {obj.end_date})"


class ClientCreateForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    last_name = forms.CharField(label="Last name", max_length=100)
    first_name = forms.CharField(label="First name", max_length=100)
    phone = forms.CharField(label="Phone", max_length=20, required=False)
    birth_date = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError(_("This username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("This email already exists."))
        return email

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            role="client",
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
        client = Client.objects.create(
            user=user,
            last_name=data["last_name"],
            first_name=data["first_name"],
            email=data["email"],
            phone=data.get("phone", ""),
            birth_date=data.get("birth_date"),
        )
        return client


class ClientUpdateForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email")
    last_name = forms.CharField(label="Last name", max_length=100)
    first_name = forms.CharField(label="First name", max_length=100)
    phone = forms.CharField(label="Phone", max_length=20, required=False)
    birth_date = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["username"].initial = self.instance.user.username
            self.fields["email"].initial = self.instance.user.email
            self.fields["last_name"].initial = self.instance.last_name
            self.fields["first_name"].initial = self.instance.first_name
            self.fields["phone"].initial = self.instance.phone
            self.fields["birth_date"].initial = self.instance.birth_date
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username=username)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise ValidationError(_("This username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = User.objects.filter(email=email)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise ValidationError(_("This email already exists."))
        return email

    def save(self):
        if self.instance is None:
            raise ValidationError(_("Client instance is required."))
        data = self.cleaned_data
        user = self.instance.user
        user.username = data["username"]
        user.email = data["email"]
        user.first_name = data.get("first_name", "")
        user.last_name = data.get("last_name", "")
        user.save()
        client = self.instance
        client.last_name = data["last_name"]
        client.first_name = data["first_name"]
        client.email = data["email"]
        client.phone = data.get("phone", "")
        client.birth_date = data.get("birth_date")
        client.save()
        return client


class VehicleForm(forms.ModelForm):
    CATEGORY_CHOICES = [
        ("CITADINE", "CITADINE"),
        ("BERLINE", "BERLINE"),
        ("SUV", "SUV"),
        ("UTILITAIRE", "UTILITAIRE"),
    ]

    category = forms.ChoiceField(
        label="Category",
        choices=[("", "TOUTE")] + CATEGORY_CHOICES,
    )

    class Meta:
        model = Vehicle
        fields = [
            "brand",
            "model",
            "year",
            "daily_price",
            "status",
            "fuel_type",
            "mileage",
            "category",
            "description",
            "photo",
        ]
        labels = {
            "brand": "Brand",
            "model": "Model",
            "year": "Year",
            "daily_price": "Price per day",
            "status": "Status",
            "fuel_type": "Fuel type",
            "mileage": "Mileage",
            "category": "Category",
            "description": "Description",
            "photo": "Photo",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_category = (getattr(self.instance, "category", "") or "").strip()
        choice_values = {value for value, _label in self.CATEGORY_CHOICES}
        if current_category and current_category not in choice_values:
            self.fields["category"].choices = [("", "TOUTE"), (current_category, current_category)] + self.CATEGORY_CHOICES

        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()


class MaintenanceForm(forms.ModelForm):
    status = forms.ChoiceField(
        label="Vehicle status",
        choices=[
            ("maintaining", "Maintaining"),
            ("useable", "Useable"),
        ],
    )

    class Meta:
        model = Maintenance
        fields = [
            "vehicle",
            "date",
            "maintenance_type",
            "cost",
            "description",
            "status",
        ]
        labels = {
            "vehicle": "Vehicle",
            "date": "Date",
            "maintenance_type": "Type",
            "cost": "Cost",
            "description": "Description",
            "status": "Status",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.order_by("brand", "model")
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "vehicle",
            "category",
            "amount",
            "date",
            "description",
        ]
        labels = {
            "vehicle": "Vehicle",
            "category": "Category",
            "amount": "Amount",
            "date": "Date",
            "description": "Description",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.order_by("brand", "model")
        self.fields["vehicle"].required = False
        self.fields["vehicle"].empty_label = "General expense"
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()


class FixedChargeAlertForm(forms.ModelForm):
    class Meta:
        model = FixedChargeAlert
        fields = [
            "vehicle",
            "category",
            "due_date",
            "amount",
            "notes",
        ]
        labels = {
            "vehicle": "Vehicle",
            "category": "Charge type",
            "due_date": "Due date",
            "amount": "Amount",
            "notes": "Notes",
        }
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.order_by("brand", "model")
        self.fields["vehicle"].required = False
        self.fields["vehicle"].empty_label = "General / not linked to one car"
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()


class DepositForm(forms.ModelForm):
    reservation = ReservationChoiceField(queryset=Reservation.objects.none(), label="Reservation")

    class Meta:
        model = Deposit
        fields = [
            "reservation",
            "amount",
            "method",
            "status",
            "received_at",
            "notes",
        ]
        labels = {
            "reservation": "Reservation",
            "amount": "Deposit amount",
            "method": "Guarantee type",
            "status": "Status",
            "received_at": "Received on",
            "notes": "Notes",
        }
        widgets = {
            "received_at": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reservation"].queryset = (
            Reservation.objects.select_related("client", "vehicle")
            .filter(deposit__isnull=True)
            .order_by("-id")
        )
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} field-input".strip()
