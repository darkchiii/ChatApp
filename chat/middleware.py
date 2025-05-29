from django.core.cache import cache
from rest_framework.response import Response
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.renderers import JSONRenderer

class RateLimitMiddleware(MiddlewareMixin):
    RATE_LIMIT = 5
    TIME_PERIOD = 10

    def _get_ip(self, request):
        return request.META.get("REMOTE_ADDR", "unknown")

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/api/messages/') and request.method == "POST": # and request.method == "POST"
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                ident = f"user_{user.id}"
            else:
                ip = self._get_ip(request)
                ident = f"ip_{ip}"
            print("path:", request.path)

            cache_key = f'rate_limit_{ident}'
            # cache_key = f'rate_limit_{user.id}'

            print("RateLimiter: request.path =", request.path)
            print("RateLimiter: user =", user)
            print("RateLimiter: cache_key =", cache_key)

            added = cache.add(cache_key, 1, timeout=self.TIME_PERIOD)
            if not added:
                count = cache.incr(cache_key)

                if count > self.RATE_LIMIT:
                    response = Response({"error": "Too many requests!"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                    response.accepted_renderer = JSONRenderer()
                    response.accepted_media_type = "application/json"
                    response.renderer_context = {}
                    response.render()

                    # print("RateLimiter: request.path =", request.path)
                    # print("RateLimiter: user =", request.user)
                    # print("RateLimiter: cache_key =", cache_key)
                    return response
            else:
                count = 1
            # cache.incr(cache_key)
        return None