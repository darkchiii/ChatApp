from rest_framework import serializers
from .models import Room, Message
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class RoomSerializer(serializers.ModelSerializer):
    user1 = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user1_readable = serializers.PrimaryKeyRelatedField(source='user1', read_only=True)
    user2 = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Room
        fields = ['id', 'user1', 'user1_readable', 'user2', 'name']

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.ReadOnlyField(source='sender.username')
    class Meta:
        model = Message
        fields = ['content', 'room', 'sender']