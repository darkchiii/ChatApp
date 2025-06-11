from ..models import Message, Room
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from django_redis import get_redis_connection

@pytest.mark.django_db
class TestRateLimiting:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.test_user1 = User.objects.create_user(username="user1", password="secret1")
        self.test_user2 = User.objects.create_user(username="user2", password="secret2")
        self.test_room = Room.objects.create(user1=self.test_user1, user2=self.test_user2)
        self.message = Message.objects.create(content="New message!", room=self.test_room, sender=self.test_user1)
        self.url_list = reverse('messages-list')


    def test_rate_limiting(self):
        token = RefreshToken.for_user(self.test_user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        redis_conn = get_redis_connection("default")

        key = f"throttle_user_{self.test_user1.id}"
        redis_conn.delete(key)

        for i in range(3):
            response = self.client.post(self.url_list, {"content": "Message !!",
                                                   "room": self.test_room.id})
            timestamps = redis_conn.zrange(key, 0, -1, withscores=True)
            # print("Request: ", i+1, "Response: ", response.status_code, "timestamp: ", timestamps)


        count = redis_conn.zcard(key)
        assert count == 3
