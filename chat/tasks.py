from datetime import timedelta
from celery import shared_task
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from redis import Redis
from messaging_app import settings

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def notify_user_new_message(self, sender_id, reciever_id, message_text):
    try:
        sender = User.objects.get(pk = sender_id)
        reciever = User.objects.get(pk=reciever_id)

        if reciever.username == "fail":
            raise Exception("Testowy wyjątek – symulacja błędu")

        result = {
            "status": f"New Message! {sender.username} sent message to {reciever.username}: {message_text}",
            "code": 200
        }
        print(result)
        return result

    except User.DoesNotExist:
        return {"status": "User object does not exist", "code": 404}

    except Exception as e:
        print(f"Retry error: {e}")
        raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_email_notification(self, user_id, message_text):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {"status": "User object does not exist", "code": 404}

    if not user.email:
        return {"status": "User has no email", "code": 400}

    send_mail(
            subject="New message waits for you!",
            message=message_text,
            from_email="noreply@chatapp.com",
            recipient_list=[user.email],
        )
    return {"status": "Email sent", "code": 200}