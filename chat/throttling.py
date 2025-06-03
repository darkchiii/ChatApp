import time
import redis
from rest_framework.throttling import SimpleRateThrottle, BaseThrottle
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework import status
from django_redis import get_redis_connection

# Uses sliding window algorithm
class MessageSendLimiter(BaseThrottle):
    RATE_LIMIT = 3
    TIME_WINDOW = 5

    def allow_request(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return None

        redis_conn = get_redis_connection("default")
        key = f'throttle_user_{request.user.id}'

        now = time.time()

        start_window = now - self.TIME_WINDOW
        redis_conn.zremrangebyscore(key, 0, start_window)
        count = redis_conn.zcard(key)

        if count < self.RATE_LIMIT:
            redis_conn.zadd(key, {str(now): now})
            return True
        return False

    # ZREMRANGEBYSCORE - usuwa elementy poza oknem czasu, key - user, min-max - usuwa wszytsko poniedzy
    # ZCARD - sprawdza ile wpisow jest w oknie dla danego user
    # jeśli mniej niz limit - wpuszcza, jesli limit przekroczony 429