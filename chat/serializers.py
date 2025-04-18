from rest_framework import serializers
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_photo', 'role']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_photo = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_name', 'sender_photo', 'sender_role',
                  'content', 'timestamp', 'formatted_timestamp', 'is_read']
        read_only_fields = ['timestamp', 'is_read']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}"

    def get_sender_photo(self, obj):
        if obj.sender.profile_photo:
            return obj.sender.profile_photo.url
        return None

    def get_sender_role(self, obj):
        return obj.sender.role

    def get_formatted_timestamp(self, obj):
        return obj.timestamp.strftime("%b %d, %Y %H:%M")

class ChatRoomSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    employee_photo = serializers.SerializerMethodField()
    manager_photo = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    name = serializers.CharField(required=False)

    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'employee', 'employee_name', 'employee_photo',
                  'manager', 'manager_name', 'manager_photo', 'created_at',
                  'updated_at', 'last_message', 'unread_count']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        # Print validation data for debugging
        print(f"Validating chat room data: {data}")

        # Check if we're in create mode (no instance) or update mode
        if self.instance is None:  # Create mode
            # For managers, employee is required
            request = self.context.get('request')
            if request and request.user.role == 'Manager':
                if 'employee' not in data:
                    raise serializers.ValidationError({'employee': 'Employee is required when a manager creates a chat room'})
            # For employees, manager is required
            elif request and request.user.role == 'Employee':
                if 'manager' not in data:
                    raise serializers.ValidationError({'manager': 'Manager is required when an employee creates a chat room'})

        return data

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_manager_name(self, obj):
        return f"{obj.manager.first_name} {obj.manager.last_name}"

    def get_employee_photo(self, obj):
        if obj.employee.profile_photo:
            return obj.employee.profile_photo.url
        return None

    def get_manager_photo(self, obj):
        if obj.manager.profile_photo:
            return obj.manager.profile_photo.url
        return None

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return {
                'content': last_message.content[:50] + ('...' if len(last_message.content) > 50 else ''),
                'timestamp': last_message.timestamp.strftime("%b %d, %H:%M"),
                'sender_id': last_message.sender.id
            }
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()
