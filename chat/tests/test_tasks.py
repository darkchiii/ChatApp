from unittest.mock import patch
import pytest
from redis import Redis
from rest_framework.test import APIClient

from messaging_app import settings
from ..models import Room, Message
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from ..tasks import notify_user_new_message, send_email_notification, notify_user_unread_messages
from django.core.exceptions import ObjectDoesNotExist
from django.core import mail

@pytest.mark.django_db
class TestTasks:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", email="user1@gmail.com", password="secret1") #email="user1@gmail.com",
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.url = reverse("messages-list")

        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )

        for key in self.redis.scan_iter("send_email_user_*"):
            self.redis.delete(key)


    @patch("chat.tasks.notify_user_new_message.delay")
    def test_notify_task_triggered(self, mock_notify):

        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        # url = reverse("messages-list")
        data = {"content": "Hello!", "room": self.test_room.id}

        response = self.client.post(self.url, data)

        assert response.status_code == 201
        mock_notify.assert_called_once()

        _, kwargs = mock_notify.call_args

        assert Message.objects.count() == 1
        assert kwargs["sender_id"] == self.test_user1.id
        assert kwargs["reciever_id"] == self.test_user2.id
        assert kwargs["message_text"] == "Hello!"

    def test_notify_user_print_message(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        notify_user_new_message(self.test_user1.id, self.test_user2.id, "Hello, test message!")

    def test_false_user_id(self):
        # with pytest.raises(ObjectDoesNotExist):
        response = notify_user_new_message(9999, 99999, "Hello!")
        assert response['code'] == 404


    @patch("chat.tasks.notify_user_new_message.delay")
    def test_empty_message_task_not_triggered(self, mock_notify):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        data = {
            "content": "",
            "room": self.test_room.id
        }
        response = self.client.post(self.url, data)
        assert response.status_code == 400
        mock_notify.assert_not_called()
        assert Message.objects.count() == 0

    @patch("chat.tasks.notify_user_new_message.delay")
    def test_reverse_users(self, mock_notify):
        token = RefreshToken.for_user(self.test_user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "content": "Reverse users test",
            "room": self.test_room.id
        }
        response = self.client.post(self.url, data)

        assert response.status_code == 201
        mock_notify.assert_called_once()

        _, kwargs = mock_notify.call_args

        assert Message.objects.count() == 1
        assert kwargs["sender_id"] == self.test_user2.id
        assert kwargs["reciever_id"] == self.test_user1.id
        assert kwargs["message_text"] == "Reverse users test"

    def test_send_email_user_with_email(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        response = send_email_notification(self.test_user1.id, "Test message")
        print(f"Test sending mail response: ",response)
        assert len(mail.outbox) == 1
        assert "Test message" in mail.outbox[0].body
        assert response['code'] == 200

    def test_send_email_user_without_email(self):
        token = RefreshToken.for_user(self.test_user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        response = send_email_notification(self.test_user2.id, "Test message")
        assert response['code'] == 400
        assert len(mail.outbox) == 0

    @patch("chat.tasks.send_email_notification.delay")
    def test_no_notification_for_second_message(self, mock_notify):
        token = RefreshToken.for_user(self.test_user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data1 = {"content": "Hello, email should be send!", "room": self.test_room.id}
        data2 = {"content": "Hello, email shouldn't be send!", "room": self.test_room.id}
        response1 = self.client.post(self.url, data1)
        response2 = self.client.post(self.url, data2)

        assert Message.objects.count() == 2
        assert mock_notify.call_count == 1

    @patch("chat.tasks.send_mail", side_effect=Exception("SMTP failed"))
    def test_send_email_retry_on_exception(self, mock_send_mail):
        with pytest.raises(Exception):
            send_email_notification(self.test_user1.id, "Retry me")

        assert mock_send_mail.called

    def test_notify_user_forced_retry(self):
        test_user_fail = User.objects.create_user(username="fail", email="fail@mail.com", password="fail123")
        with pytest.raises(Exception):
            notify_user_new_message(self.test_user1.id, test_user_fail.id, "force retry")

    def test_notify_user_does_not_exist_no_retry(self):
        response = notify_user_new_message(9999, 99999, "will not retry")
        assert response["code"] == 404

    def test_send_email_user_does_not_exist(self):
        response = send_email_notification(9999, "should not retry")
        assert response["code"] == 404

    @patch("chat.tasks.notify_user_new_message.apply_async")
    def test_notify_user_delayed_execution(self, mock_async):
        notify_user_new_message.apply_async(
            args=[self.test_user1.id, self.test_user2.id, "Delayed"],
            countdown=10
        )
        mock_async.assert_called_once()

    def test_task_apply_direct_success(self):
        result = notify_user_new_message.apply(args=[self.test_user1.id, self.test_user2.id, "Inline test"])
        assert result.successful()
        assert result.result["code"] == 200

    def test_notify_user_with_unread_messages(self, caplog):
        user1 = User.objects.create_user(username="alice", password="test")
        user2 = User.objects.create_user(username="anna", password="test")
        room = Room.objects.create(user1=user1, user2=user2)

        Message.objects.create(content="Hi!", room=room, sender=user2, is_read=False)

        with caplog.at_level("WARNING"):
            notify_user_unread_messages()

        assert "[alice] You have 1 unread messages." in caplog.text
        assert "[anna]" not in caplog.text

    @pytest.mark.django_db
    def test_notify_user_with_no_unread_messages(self, caplog):
        user1 = User.objects.create_user(username="charlie", password="test")
        user2 = User.objects.create_user(username="daria", password="test")
        room = Room.objects.create(user1=user1, user2=user2)

        Message.objects.create(content="Hello!", room=room, sender=user2, is_read=True)

        with caplog.at_level("WARNING"):
            notify_user_unread_messages()

        assert "[charlie]" not in caplog.text
        assert "[daria]" not in caplog.text
