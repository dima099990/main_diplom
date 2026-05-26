from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0008_branches_m2m_appointment_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='pd_consent',
            field=models.BooleanField(default=False, verbose_name='Согласие на ПД'),
        ),
        migrations.AddField(
            model_name='customer',
            name='pd_consent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата согласия на ПД'),
        ),
    ]
