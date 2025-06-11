import pytest
from rest_framework.test import APIClient
from ..models import Room, Message
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from django.core.cache import cache
from django_redis import get_redis_connection
from rest_framework.settings import api_settings
from django.test import override_settings
import json

# Test list rooms
@pytest.mark.django_db
class TestListRoom:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.url_list = reverse('rooms-list')
        # get_redis_connection("default").flushdb()
        redis_conn = get_redis_connection("default")
        redis_conn.delete(f"throttle_user_{self.test_user1.id}")


    def test_response_data(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        response = self.client.get(self.url_list)
        assert response.data[0]['user1_readable'] == self.test_user1.id

        assert response.data[0]['user2'] == self.test_user2.id
        assert response.data[0]['name'] == "Chat"

    def test_room_list_logged_in_user(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        response = self.client.get(self.url_list)
        assert response.status_code == 200
        assert response.data[0]['user1_readable'] == self.test_user1.id
        assert response.data[0]['user2'] == self.test_user2.id

    def test_room_list_not_authenticated(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 401

    def test_response_no_rooms(self):
        self.test_user = User.objects.create_user(username="user", password="secret")
        token = RefreshToken.for_user(self.test_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        response = self.client.get(self.url_list)
        assert response.status_code == 404

    def test_list_single_room(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        response = self.client.get(self.url_list)
        assert len(response.data) == 1

    def test_multiple_rooms(self):
        self.test_user3 = User.objects.create_user(username="user3", password="secret3")
        self.test_user4 = User.objects.create_user(username="user4", password="secret4")
        self.test_user5 = User.objects.create_user(username="user5", password="secret5")
        self.test_room1 = Room.objects.create(user1=self.test_user1, user2=self.test_user3)
        self.test_room2 = Room.objects.create(user1=self.test_user1, user2=self.test_user4)
        self.test_room3 = Room.objects.create(user1=self.test_user1, user2=self.test_user5)
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')

        response = self.client.get(self.url_list)
        assert isinstance(response.data, list)
        assert all(isinstance(r, dict) for r in response.data)
        assert len(response.data) == 4

    # Testing is_read field status in Message model
    def test_read_status_is_updated_on_message_list(self):
        print("\nTest; test_read_status_is_updated_on_message_list")
        get_redis_connection("default").flushdb()

        token = RefreshToken.for_user(self.test_user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "content": "test unread",
            "room": self.test_room.id
        }
        response_post = self.client.post(reverse('messages-list'), data)

        message_to_read = Message.objects.get(sender=self.test_user2, room = self.test_room)
        assert message_to_read.is_read is False

        print('before', message_to_read.is_read)
        token2 = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token2.access_token)}')
        url = reverse('rooms-messages', kwargs={'pk': self.test_room.id})
        response = self.client.get(url)

        message_to_read.refresh_from_db()

        print('after', message_to_read.is_read)

        print("response data from GET:", response.data)
        print("from DB:", message_to_read.is_read)
        assert message_to_read.is_read is True
        assert message_to_read.time_read is not None

# Test create rooms
@pytest.mark.django_db
class TestCreateRoom:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.url_list = reverse('rooms-list')

    def test_create_room(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "user2": self.test_user2.id
        }
        response = self.client.post(self.url_list, data)
        # print(response)
        assert response.status_code == 201
        assert Room.objects.filter(user1=self.test_user1, user2=self.test_user2).exists()

    def test_chat_with_self(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "user2": self.test_user1.id
        }
        response = self.client.post(self.url_list, data)
        assert response.status_code == 201
        assert Room.objects.filter(user1=self.test_user1, user2=self.test_user1).exists()

    def test_response_user2_not_provided(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
        }
        response = self.client.post(self.url_list, data)
        assert response.status_code == 400

    def test_response_user2_not_exists(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        invalid_id = 9999
        data = {
            "user2": invalid_id
        }
        response = self.client.post(self.url_list, data)
        assert response.status_code == 404

    def test_response_user2_ivalid_format(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        data = {
            "user2": "invalid"
        }
        response = self.client.post(self.url_list, data)
        assert response.status_code == 400

    def test_unauthorized_user2_exists(self):
        data = {
            "user2": self.test_user1.id
        }
        response = self.client.post(self.url_list, data)
        assert response.status_code == 401


    def test_response_data_success(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        self.test_user10 = User.objects.create_user(username="user10", password="secret1")
        data = {
            "user2": self.test_user10.id
        }
        response = self.client.post(self.url_list, data)
        # print(response.data)

    # test redirect if room already exists

@pytest.mark.django_db
class TestCacheMessages:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.message = Message.objects.create(content="New message!", room=self.test_room, sender=self.test_user1)
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        self.url_list = reverse('rooms-messages', args=[self.test_room.pk])

    def test_cache_is_set(self):
        redis_conn = get_redis_connection("default")
        # redis_conn.delete(f"messages_room_{self.test_room.pk}")

        response = self.client.get(self.url_list)
        assert response.status_code == 200
        # print("response cache is set", response.data)
        cached = redis_conn.lrange(f"messages_room_{self.test_room.pk}", 0, 49)
        # print("test cache is set", cached)
        assert cached

    # def test_create_message_first_in_cache(self):
    #     self.url_list_post = reverse('messages-list')
    #     # cache.delete(f"throttle_user_{self.test_user1.id}")

    #     redis_conn = get_redis_connection("default")
    #     redis_conn.delete(f"throttle_user_{self.test_user1.id}")


    #     data = {
    #         "content": "Testing if new message first in cache",
    #         "room": self.test_room.id,
    #     }
    #     response = self.client.post(self.url_list_post, data)
    #     assert response.status_code == 201
    #     cached_raw = redis_conn.lrange(f"messages_room_{self.test_room.pk}", 0, 0)
    #     assert cached_raw

    #     first_cached_message = json.loads(cached_raw[0].decode())

    #     assert first_cached_message["content"] == data["content"]
    #     assert first_cached_message["room"] == data["room"]
