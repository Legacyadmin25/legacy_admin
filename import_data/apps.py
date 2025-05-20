# import_data/apps.py

from django.apps import AppConfig

class ImportDataConfig(AppConfig):
    """
    Configuration for the Import Data app.
    Specifies the name of the app and the default auto field type.
    """
    default_auto_field = 'django.db.models.BigAutoField'  # Using BigAutoField for default primary keys
    name = 'import_data'  # App name should match the directory name exactly
    verbose_name = "Import Data"  # Optional: Useful for displaying in admin, or other Django features
