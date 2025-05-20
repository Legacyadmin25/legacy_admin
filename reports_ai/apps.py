from django.apps import AppConfig


class ReportsAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports_ai'
    verbose_name = 'AI Reports'
    
    def ready(self):
        # Import signals to register them
        from . import signals
        signals.connect_signals()
