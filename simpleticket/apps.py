from django.apps import AppConfig

class YourAppNameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_simpleticket'

    def ready(self):
        import django_simpleticket.signals  # Ensure signals are imported


class SimpleticketConfig(AppConfig):
    name = 'simpleticket'

