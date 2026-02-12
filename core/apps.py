from django.apps import AppConfig
import sys
import os
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals
        if self.is_manage_py_command():
            return


        try:
            self.set_telegram_webhook()
        except Exception as e:
            logger.error(f"Webhook ornatiwda qatelik: {e}")

    def is_manage_py_command(self):
 
        if not sys.argv:
            return False

        ignored_commands = ['migrate', 'makemigrations', 'collectstatic', 'test', 'createsuperuser']
        
        for cmd in ignored_commands:
            if cmd in sys.argv:
                return True
        return False

    def set_telegram_webhook(self):
        import requests
        from django.conf import settings
        
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', None)
        
        if not token or not webhook_url:
            logger.warning("Telegram token yamasa Webhook URL settings.py faylinda tabilmadi.")
            return

        if not webhook_url.startswith('https://'):
            logger.warning(f"Diqqat! Webhook URL 'https' boliwi kerek. Házirgi: {webhook_url}")

        url = f"https://api.telegram.org/bot{token}/setWebhook"
        
        try:
           
            response = requests.post(url, json={"url": webhook_url}, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Telegram Webhook ornatildi: {webhook_url}")
            else:
                logger.error(f"Webhook ornatilmadi: {response.text}")
        except requests.exceptions.RequestException as e:
      
            logger.error(f"Telegramga jalganip bolmadi: {e}")