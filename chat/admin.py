from django.contrib import admin
from .models import Room, Message, UserProfile
# Register your models here.

admin.site.register(Message)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2')