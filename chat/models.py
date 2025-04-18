from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ChatRoom(models.Model):
    """Model for chat rooms between employees and managers"""
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Participants
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='employee_chat_rooms',
        limit_choices_to={'role': 'Employee'}
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manager_chat_rooms',
        limit_choices_to={'role': 'Manager'}
    )

    class Meta:
        unique_together = ['employee', 'manager']

    def __str__(self):
        return f"{self.name} ({self.employee.username} - {self.manager.username})"

    def save(self, *args, **kwargs):
        # Auto-generate room name if not provided
        if not self.name:
            self.name = f"chat_{self.employee.username}_{self.manager.username}"
        super().save(*args, **kwargs)

class Message(models.Model):
    """Model for individual chat messages"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
