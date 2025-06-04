from unittest.mock import patch
import pytest
from rest_framework.test import APIClient
from ..models import Room, Message
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from ..tasks import notify_user_new_message
from django.core.exceptions import ObjectDoesNotExist

@pytest.mark.django_db
class TestTasks:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.url = reverse("messages-list")

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
        with pytest.raises(ObjectDoesNotExist):
            notify_user_new_message(9999, 99999, "Hello!")

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
