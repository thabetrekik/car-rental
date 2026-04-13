import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_deposit"),
    ]

    operations = [
        migrations.CreateModel(
            name="FixedChargeAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("insurance", "Insurance"), ("technical_inspection", "Technical Inspection"), ("vignette", "Vignette"), ("bank_installment", "Bank Installment")], max_length=40)),
                ("due_date", models.DateField()),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed")], default="pending", max_length=20)),
                ("completed_at", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fixed_charge_alerts", to="accounts.vehicle")),
            ],
            options={
                "db_table": "fixed_charge_alert",
            },
        ),
    ]
