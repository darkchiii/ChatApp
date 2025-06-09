from datetime import timedelta
from redis import Redis
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.models import User

from messaging_app import settings
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer
from django.core.cache import cache
from rest_framework.decorators import action
import json
from django_redis import get_redis_connection
from .throttling import MessageSendLimiter
from .tasks import notify_user_new_message, send_email_notification

class RoomViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    # List logged in user rooms
    def list(self, request):
        user = request.user
        user_rooms = Room.objects.filter(Q(user1=user) | Q(user2=user))
        # print(user_rooms.first().name)
        if user_rooms.exists():
            serializer = RoomSerializer(user_rooms, many=True)
            # print("list rooms: ", serializer.data)
            # print(request.data)
            return Response(serializer.data, status=200)
        return Response({"error": "You don't have any chats :("}, status=status.HTTP_404_NOT_FOUND)

    # Create new room
    def create(self, request):
    # Check if room already exists, then redirect
        data = request.data.get('user2')
        user = request.user

        try:
            user2_id = int(data)
        except (ValueError, TypeError):
            return Response({"error": "Invalid user ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user2 = User.objects.get(id=data)
            try:
                room_exists = Room.objects.get(
                    (Q(user1=user) & Q(user2=user2)) | (Q(user1=user2) & Q(user2=user))
                        ).exists()

            except Room.DoesNotExist:
                data = {
                    "user1": user.pk,
                    "user2": user2.pk
                }
                serializer = RoomSerializer(data=data, context = {'request': request})
                if serializer.is_valid():
                    room = serializer.save(user1=request.user)
                    return Response({"data": RoomSerializer(room).data,
                                    "status": "Room created"}, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # Room details
    def retrieve(self, request, pk):
        user = request.user
        try:
            room = Room.objects.get(id=pk)
            if room.user1 != user or room.user2 != user:
                return Response({"error": "Not authorized."}, status=status.HTTP_401_UNAUTHORIZED)
            serializer = RoomSerializer(instance=room)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Room.DoesNotExist:
            return Response({"error": "Room doesn't exist!"}, status=status.HTTP_404_NOT_FOUND)

    # List last 50 messages from room
    @action(detail=True, methods=["get"], url_name='messages', url_path='messages') #rooms/pk/messages
    def messages(self, request, pk=None):
        try:
            room = Room.objects.get(id=pk)
            if room.user1 != request.user and room.user2 != request.user:
                return Response({"error": "Not authorized."}, status=status.HTTP_401_UNAUTHORIZED)

            redis_conn = get_redis_connection("default")
            cache_key = f'messages_room_{pk}'
            raw_messages = redis_conn.lrange(cache_key, 0, 49)

            if raw_messages:
                print("Cache hit")
                messages = [json.loads(m) for m in raw_messages]
                return Response(messages, status=status.HTTP_200_OK)

            print("Cache miss")
            messages = Message.objects.filter(room=room.id).order_by('-time')[:50][::-1]
            serializer = MessageSerializer(messages, many=True)
            for message in serializer.data:
                redis_conn.lpush(cache_key, json.dumps(message))
                redis_conn.expire(cache_key, 86400)
            redis_conn.ltrim(cache_key, 0, 49)
            return Response(serializer.data, status=200)

        except Room.DoesNotExist:
            return Response({"error": "Room doesn't exist!"}, status=status.HTTP_404_NOT_FOUND)


class MessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MessageSendLimiter]

    def create(self, request):
        print(request.data)
        room_id = request.data.get('room')
        sender = request.user
        # reciever_id = message.room.user1.id if sender.id==room.user2.id else message.room.user2.id

        r = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True
        )
        # redis_key = f"send_email_user_{reciever_id}"

        try:
            room = Room.objects.get(id = room_id)
            reciever_id = room.user1.id if sender.id==room.user2.id else room.user2.id
            redis_key = f"send_email_user_{reciever_id}"

            if room.user1 != sender and room.user2 != sender:
                return Response({"error": "Not authorized."}, status=status.HTTP_401_UNAUTHORIZED)
            serializer = MessageSerializer(data=request.data)
            if serializer.is_valid():
                redis_conn = get_redis_connection("default")
                message = serializer.save(sender=sender)

                notify_user_new_message.delay(
                    sender_id = message.sender.id,
                    reciever_id = reciever_id,
                    message_text = message.content)
                if r.exists(redis_key):
                    print("Mail already sent, skipping task")
                    return Response({"status": "Skipped, already sent recently"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                else:
                    send_email_notification.delay(reciever_id,
                                                message_text = message.content
                                                )
                    r.set(redis_key, "send", ex=timedelta(minutes=30))

                json_string = json.dumps(MessageSerializer(message).data)
                redis_conn.lpush(f'messages_room_{room_id}', json_string)
                redis_conn.ltrim(f'messages_room_{room_id}', 0, 49)

                return Response({"data": MessageSerializer(message).data,
                                 "status": "Message sent"}, status=status.HTTP_201_CREATED
                                )
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

