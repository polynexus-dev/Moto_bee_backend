from django.apps import AppConfig
import sys


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Don't start scheduler during migrations, shell, or other management commands
        if 'runserver' not in sys.argv and 'daphne' not in sys.argv:
            return

        from . import scheduler
        scheduler.start()