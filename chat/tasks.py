from datetime import timedelta
from celery import shared_task
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from redis import Redis

from messaging_app import settings


@shared_task
def notify_user_new_message(sender_id, reciever_id, message_text):
    try:
        sender = User.objects.get(pk = sender_id)
        reciever = User.objects.get(pk=reciever_id)
    except User.DoesNotExist:
        return {"status": "User object does not exist", "code": 404}

    print(f"Masz wiadomość! {sender.username} wysłał wiadomość {reciever.username}: {message_text}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def send_email_notification(self, user_id, message_text):
    # r = Redis(
    # host=settings.REDIS_HOST,
    # port=settings.REDIS_PORT,
    # db=0,
    # decode_responses=True
    # )
    # redis_key = f"send_email_user_{user_id}"
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {"status": "User object does not exist", "code": 404}

    if not user.email:
        return {"status": "User has no email", "code": 400}

    # if r.exists(redis_key):
        # print("Mail already sent, skipping task")
        # return {"status": "Skipped, already sent recently", "code": 429}
    # else:
    send_mail(
            subject="New message waits for you!",
            message=message_text,
            from_email="noreply@chatapp.com",
            recipient_list=[user.email],
        )
        # r.set(redis_key, "send", ex=timedelta(minutes=30))
    return {"status": "Email sent", "code": 200}