from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', limit_choices_to={'role': 'Employee'})
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks', limit_choices_to={'role': 'Manager'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    document = models.FileField(upload_to='documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    assigned_at = models.DateTimeField(auto_now_add=True)  # Added for dashboard history tracking

    def __str__(self):
        return self.title

    def is_overdue(self):
        if self.due_date and timezone.now() > self.due_date:
            return True
        return False

    def days_remaining(self):
        if not self.due_date:
            return None
        delta = self.due_date - timezone.now()
        return max(0, delta.days)

class TaskAssignment(models.Model):
    """
    Tracks detailed information about task assignments to employees.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_assignments', limit_choices_to={'role': 'Employee'})
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ['task', 'employee']
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.task.title} - {self.employee.username}"

    def accept_assignment(self):
        self.accepted = True
        self.accepted_at = timezone.now()
        self.save()

    def complete_assignment(self, hours_spent):
        self.actual_hours = hours_spent
        self.completed_at = timezone.now()
        self.save()

        # Update task status
        self.task.status = 'completed'
        self.task.progress = 100
        self.task.save()

class TaskProgress(models.Model):
    """
    Tracks progress updates for tasks.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='progress_updates')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_updates')
    progress_percentage = models.IntegerField(help_text="Progress percentage (0-100)")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Progress update for {self.task.title}: {self.progress_percentage}%"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update the task's progress field
        self.task.progress = self.progress_percentage

        # If progress is 100%, mark task as completed
        if self.progress_percentage == 100:
            self.task.status = 'completed'
        # If progress is between 1-99%, mark as in_progress
        elif self.progress_percentage > 0:
            self.task.status = 'in_progress'

        self.task.save()
