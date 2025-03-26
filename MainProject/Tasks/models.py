from django.db import models
from Users.models import User

class Task(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(
        User, related_name='tasks', 
        on_delete=models.CASCADE, limit_choices_to={'role': 'employee'}
    )
    created_by = models.ForeignKey(
        User, related_name='created_tasks', 
        on_delete=models.CASCADE, limit_choices_to={'role': 'manager'}
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# Improvement request from a client
class ImprovementRequest(models.Model):
    task = models.ForeignKey(Task, related_name='improvement_requests', on_delete=models.CASCADE)
    client = models.ForeignKey(
        User, related_name='improvement_requests', 
        on_delete=models.CASCADE, limit_choices_to={'role': 'client'}
    )
    improvement_details = models.TextField()
    status = models.CharField(max_length=20, choices=(('pending', 'Pending'), ('resolved', 'Resolved')), default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Improvement Request for {self.task.title}"
