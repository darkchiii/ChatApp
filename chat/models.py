from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField()

class Room(models.Model):
    name = models.CharField(max_length=50, default="Chat")
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="room_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="room_user2")

    def clean(self):
        if self.user1 == self.user2:
            raise ValidationError("You can't chat with yourself!")


class Message(models.Model):
    content = models.TextField()
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_message")
    time = models.DateTimeField(auto_now_add=True)