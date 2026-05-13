from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_fixed_charge_alert"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("cin", "CIN"),
                    ("driving_license", "Driving Licence"),
                ],
                default="cin",
                max_length=30,
            ),
        ),
    ]
