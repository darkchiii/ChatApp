from celery import shared_task
from django.contrib.auth.models import User

@shared_task
def notify_user_new_message(sender_id, reciever_id, message_text):
    sender = User.objects.get(pk = sender_id)
    reciever = User.objects.get(pk=reciever_id)

    print(f"Masz wiadomość! {sender.username} wysłał wiadomość {reciever.username}: {message_text}")
