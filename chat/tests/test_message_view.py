import pytest
from rest_framework.test import APIClient
from ..models import Message, Room
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from django.core.cache import cache
from django_redis import get_redis_connection

@pytest.mark.django_db
class TestCreateMessage:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.url_list = reverse('messages-list')

    def test_send_message_success(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "content": "Lorem ipsum",
            "room": self.test_room.id
        }
        response = self.client.post(self.url_list, data)
        # print(response.data)
        assert response.status_code == 201

    def test_send_empty_message(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "content": "",
            "room": self.test_room.id
        }
        response = self.client.post(self.url_list, data)
        # print(f"Send empty message status code: ", response.status_code)
        assert response.status_code == 400

