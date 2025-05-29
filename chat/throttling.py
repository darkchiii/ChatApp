from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework import status

class MessageRateThrottle(SimpleRateThrottle):
    # RATE_LIMIT = 5
    # TIME_PERIOD = 10

    # def get_cache_key(self, request, view):
    #     if request.user and request.user.is_authenticated:
    #         return f'throttle_user_{request.user.id}'

    # def allow_request(self, request, view):
    #     cache_key = self.get_cache_key(request, view)
    #     if cache_key is None:
    #         return True

    #     added = cache.add(cache_key, 1, timeout=self.TIME_PERIOD)

    #     if not added:
    #         count = cache.incr(cache_key)

    #         if count > self.RATE_LIMIT:
    #             return False
    #     return True
    # rate = '1/s'
    scope = 'message_send'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            key = f"throttle_user_{request.user.id}"
        print("Throttle key", key)
        return key
