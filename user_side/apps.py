from django.apps import AppConfig


class UserSideConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_side'

    def ready(self):
        try:
            import user_side.signals  # Import the signals
            print("Signals imported successfully!............................")  # Debug print
        except Exception as e:
            print(f"Error importing signals:................................. {e}")  # Debug print