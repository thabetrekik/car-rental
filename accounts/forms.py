from decimal import Decimal

from django import forms


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
    start_date = forms.DateField(
        label="Start date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label="End date",
        widget=forms.DateInput(attrs={"type": "date"}),
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
