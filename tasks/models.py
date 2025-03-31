from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', limit_choices_to={'role': 'employee'})
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks', limit_choices_to={'role': 'manager'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    document = models.FileField(upload_to='documents/', null=True, blank=True)  # Document upload support
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class DocumentRequest(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='document_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('fulfilled', 'Fulfilled')], default='pending')

    def __str__(self):
        return f"Request by {self.requested_by} for {self.task.title}"
