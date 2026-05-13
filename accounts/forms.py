from decimal import Decimal

from django import forms
from django.utils import timezone


class RegistrationForm(forms.Form):
    username = forms.CharField(label="Username", max_length=100)
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    last_name = forms.CharField(label="Last name", max_length=100, required=False)
    first_name = forms.CharField(label="First name", max_length=100, required=False)
    phone = forms.CharField(label="Phone", max_length=20, required=False)
    birth_date = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )


class ReservationDetailsForm(forms.Form):
    PAYMENT_METHOD_AGENCY = "agency"
    PAYMENT_METHOD_ONLINE = "online"

    start_date = forms.DateField(
        label="Start date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label="End date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    payment_method = forms.ChoiceField(
        label="Payment method",
        choices=[
            (PAYMENT_METHOD_AGENCY, "Pay at agency"),
            (PAYMENT_METHOD_ONLINE, "Online payment"),
        ],
        widget=forms.RadioSelect,
        initial=PAYMENT_METHOD_AGENCY,
    )

    def __init__(self, *args, daily_price=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.daily_price = daily_price or Decimal("0")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if not start_date or not end_date:
            return cleaned_data

        if end_date < start_date:
            self.add_error("end_date", "End date must be after or equal to start date.")
            return cleaned_data

        number_of_days = (end_date - start_date).days + 1
        cleaned_data["number_of_days"] = number_of_days
        cleaned_data["total_price"] = self.daily_price * Decimal(number_of_days)
        return cleaned_data


class OnlinePaymentForm(forms.Form):
    card_holder = forms.CharField(label="Card holder", max_length=120)
    card_number = forms.CharField(label="Card number", min_length=12, max_length=19)
    expiry_month = forms.IntegerField(label="Month", min_value=1, max_value=12)
    expiry_year = forms.IntegerField(label="Year", min_value=timezone.localdate().year)
    cvv = forms.CharField(label="CVV", min_length=3, max_length=4, widget=forms.PasswordInput)

    def clean_card_number(self):
        card_number = "".join((self.cleaned_data["card_number"] or "").split())
        if not card_number.isdigit():
            raise forms.ValidationError("Card number must contain digits only.")
        return card_number

    def clean_cvv(self):
        cvv = self.cleaned_data["cvv"]
        if not cvv.isdigit():
            raise forms.ValidationError("CVV must contain digits only.")
        return cvv

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("expiry_month")
        year = cleaned_data.get("expiry_year")
        today = timezone.localdate()

        if month and year and (year < today.year or (year == today.year and month < today.month)):
            self.add_error("expiry_month", "Card expiry date must be in the future.")
        return cleaned_data


class ClientDocumentForm(forms.Form):
    cin_file = forms.FileField(label="CIN", required=False)
    driving_license_file = forms.FileField(label="Driving Licence", required=False)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("cin_file") and not cleaned_data.get("driving_license_file"):
            raise forms.ValidationError("Upload at least one document.")
        return cleaned_data
