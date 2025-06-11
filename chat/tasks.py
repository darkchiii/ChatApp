from datetime import timedelta
from celery import shared_task
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from redis import Redis
from messaging_app import settings
from .models import Message, Room
from django.db.models import Q
import logging
logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def notify_user_new_message(self, sender_id, reciever_id, message_text):
    try:
        sender = User.objects.get(pk = sender_id)
        reciever = User.objects.get(pk=reciever_id)

        if reciever.username == "fail":
            raise Exception("Error simulation")

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
def notify_user_unread_messages(self):
    users = User.objects.all()

    for u in users:
        rooms = Room.objects.filter(Q(user1 = u) | Q(user2= u))
        unread_messages = 0
        for r in rooms:
            count = Message.objects.filter(room=r, is_read=False).exclude(sender=u).count()
            unread_messages += count
        if unread_messages > 0:
            logger.warning(f"[{u.username}] You have {unread_messages} unread messages.")


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