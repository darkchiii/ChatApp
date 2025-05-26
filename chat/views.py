from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer
# from rest_framework_simplejwt.authentication import JWTAuthentication



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
            #Zobaczyc co zwraca serializer
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
                serializer = RoomSerializer(data=data)
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

class MessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        print(request.data)
        room_id = request.data.get('room')
        sender = request.user
        try:
            room = Room.objects.get(id = room_id)
            if room.user1 != sender and room.user2 != sender:
                return Response({"error": "Not authorized."}, status=status.HTTP_401_UNAUTHORIZED)
            serializer = MessageSerializer(data=request.data)
            if serializer.is_valid():
                message = serializer.save(sender=sender)
                return Response({"data": MessageSerializer(message).data,
                                 "status": "Message sent"}, status=status.HTTP_201_CREATED
                                )
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

    #List last 50 messages from room
    def list(retrieve, request, pk):
        try:
            room = Room.objects.get(id=pk)
            if room.user1 != request.user and room.user2 != request.user:
                return Response({"error": "Not authorized."}, status=status.HTTP_401_UNAUTHORIZED)

            messages = Message.objects.filter(room=room.id)
            if messages.exists():
                serializer = MessageSerializer(messages, many=True)
                return Response(serializer.data, status=200)
            return Response({"error": "You don't have any chats :("}, status=status.HTTP_404_NOT_FOUND)

        except Room.DoesNotExist:
            return Response({"error": "Room doesn't exist!"}, status=status.HTTP_404_NOT_FOUND)
