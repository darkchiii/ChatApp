from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='rooms')
router.register(r'messages', MessageViewSet, basename='messages')

urlpatterns = [
    path('api/', include(router.urls)),
    # path('api/room/<:pk>/messages', RoomViewSet.mess)
]