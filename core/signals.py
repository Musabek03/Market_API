from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser,Notification


@receiver(post_save,sender=CustomUser)
def create_user_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance, message = f"Assalawma aleykum xosh keldiniz {instance.username}!  Sizdi korgenimizden quwanishlimiz!")