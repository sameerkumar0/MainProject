from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
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
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks', limit_choices_to={'role': 'Manager'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    document = models.FileField(upload_to='documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    assigned_at = models.DateTimeField(auto_now_add=True)  # Added for dashboard history tracking

    # New fields for dashboard
    start_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

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

    def get_time_remaining(self):
        """Returns time remaining until due date in a human-readable format."""
        if not self.due_date:
            return "No deadline"
        if self.status == 'completed':
            return "Completed"

        now = timezone.now()
        if now > self.due_date:
            return "Overdue"

        delta = self.due_date - now
        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            return f"{days} days, {hours} hours"
        else:
            return f"{hours} hours"

    def save(self, *args, **kwargs):
        # Set start_date when status changes to in_progress
        if self.status == 'in_progress' and not self.start_date:
            self.start_date = timezone.now()

        # Set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            # Ensure progress is 100% when completed
            self.progress = 100

        # Reset completed_at if status changes from completed
        elif self.status != 'completed' and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        # Check if this is a new assignment (being created)
        is_new = self.pk is None

        # Save the assignment
        super().save(*args, **kwargs)

        # Create notification for the employee when a new task is assigned
        if is_new:
            from .models import Notification

            # Create notification for the employee
            Notification.objects.create(
                user=self.employee,
                notification_type='task_assigned',
                title='New Task Assigned',
                message=f'You have been assigned a new task: "{self.task.title}"',
                related_task=self.task
            )

    def accept_assignment(self):
        self.accepted = True
        self.accepted_at = timezone.now()
        self.save()

        # Update task status to 'assigned' once accepted
        self.task.status = 'assigned'
        self.task.save()

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

    # New fields for dashboard
    time_spent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hours spent on this update"
    )
    status_change = models.CharField(
        max_length=50,
        blank=True,
        help_text="Status change if any (e.g., 'pending to in_progress')"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Progress update for {self.task.title}: {self.progress_percentage}%"

    def save(self, *args, **kwargs):
        # Track status change if task status will change
        if self.pk is None:  # New progress update
            old_status = self.task.status
            new_status = None

            # Determine new status based on progress
            if self.progress_percentage == 100:
                new_status = 'completed'
            elif self.progress_percentage > 0:
                new_status = 'in_progress'

            # Record status change if different
            if new_status and old_status != new_status:
                self.status_change = f"{old_status} to {new_status}"

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

        # Create notification for the manager
        if self.task.assigned_by:
            from .models import Notification
            status_text = 'completed' if self.progress_percentage == 100 else 'updated'

            Notification.objects.create(
                user=self.task.assigned_by,
                notification_type='task_updated',
                title=f'Task {status_text}',
                message=f'{self.updated_by.get_full_name()} has {status_text} the task "{self.task.title}" with {self.progress_percentage}% progress.',
                related_task=self.task
            )


class Notification(models.Model):
    """
    Model for storing user notifications for the dashboard.
    """
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('comment_added', 'Comment Added'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('task_overdue', 'Task Overdue'),
        ('task_completed', 'Task Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type}: {self.title}"


class UserActivity(models.Model):
    """
    Model for tracking user activity for the dashboard.
    """
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('task_created', 'Task Created'),
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('progress_updated', 'Progress Updated'),
        ('comment_added', 'Comment Added'),
        ('task_completed', 'Task Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User activities'

    def __str__(self):
        return f"{self.user.username}: {self.activity_type}"
