from django.contrib import admin
from .models import ChatRoom, Message

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'manager', 'created_at', 'updated_at')
    search_fields = ('name', 'employee__username', 'manager__username')
    list_filter = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'short_content', 'timestamp', 'is_read')
    search_fields = ('content', 'sender__username')
    list_filter = ('timestamp', 'is_read', 'room')
    date_hierarchy = 'timestamp'

    def short_content(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    short_content.short_description = 'Content'
