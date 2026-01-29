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

        #Server (Docker/Runserver) iske tuskende Webhook ornatiw
        # 'RUN_MAIN' -> Django runserver reloaderi ushon (eki ret islemewi ushin)
        # Dockerde adette Gunicorn isletilse, bul shartke kirmeydi, sonliqtan
        # biz tomendegi logikani qollanamiz
        
        try:
            self.set_telegram_webhook()
        except Exception as e:
            logger.error(f"Webhook ornatiwda qatelik: {e}")

    def is_manage_py_command(self):
        """
        Hazirgi process 'migrate', 'makemigrations' yamasa 'collectstatic' ekenin tekseredi.
        """
        # Eger sys.argv bos bolsa (qandayda bir sebepler menen)
        if not sys.argv:
            return False

        # Irnorlangan  komandalar
        ignored_commands = ['migrate', 'makemigrations', 'collectstatic', 'test', 'createsuperuser']
        
        # Hazirgi komanda usi dizimde bar ma?
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

        # Nginx bolgani ushin, URL 'https://' penen baslaniwi shart
        if not webhook_url.startswith('https://'):
            logger.warning(f"Diqqat! Webhook URL 'https' boliwi kerek. Házirgi: {webhook_url}")

        url = f"https://api.telegram.org/bot{token}/setWebhook"
        
        try:
            # Timeout qosiw kerek, bolmasa Docker qatip qaliwi mumkin
            response = requests.post(url, json={"url": webhook_url}, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Telegram Webhook ornatildi: {webhook_url}")
            else:
                logger.error(f"Webhook ornatilmadi: {response.text}")
        except requests.exceptions.RequestException as e:
            # Internet joq bolsa yamasa Telegram islemese, server toqtap qalmawi kerek
            logger.error(f"Telegramga jalganip bolmadi: {e}")