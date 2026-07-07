from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cart'

    def ready(self):
        # Registers the guest-cart -> user-cart merge handler for the
        # user_logged_in signal. Imported here (not at module load time)
        # to avoid triggering model imports before the app registry is ready.
        import cart.signals  # noqa: F401
