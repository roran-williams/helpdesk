# Generated by Django 5.1.6 on 2025-03-31 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simpleticket', '0016_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_picture',
            field=models.ImageField(blank=True, default='default_profile.jpg', upload_to='profile_pics/'),
        ),
    ]
