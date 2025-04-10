from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta

class UserRoles(models.TextChoices):
    MANAGER = "Manager"
    EMPLOYEE = "Employee"

class CustomUserManager(BaseUserManager):
    """Custom manager for handling user creation."""

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # Hash the password
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and return a superuser with admin privileges."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRoles.MANAGER)  # Superuser must be a manager

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    """Custom user model with role-based access control."""
    role = models.CharField(max_length=20, choices=UserRoles.choices, default=UserRoles.EMPLOYEE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    tech_stack = models.CharField(max_length=255, null=True, blank=True)
    is_available = models.BooleanField(default=True)  # Employee availability

    # Many employees can have one manager
    manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )

    # Optional department field
    department = models.ForeignKey("Department", on_delete=models.SET_NULL, null=True, blank=True)

    # New fields for dashboard
    last_active = models.DateTimeField(null=True, blank=True)
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('busy', 'Busy'),
            ('away', 'Away')
        ],
        default='available'
    )

    objects = CustomUserManager()  # Assign custom manager

    def is_manager(self):
        return self.role == UserRoles.MANAGER

    def is_employee(self):
        return self.role == UserRoles.EMPLOYEE

    # Dashboard helper methods
    def get_completed_tasks_count(self):
        return self.tasks.filter(status='completed').count()

    def get_pending_tasks_count(self):
        return self.tasks.filter(status='pending').count()

    def get_in_progress_tasks_count(self):
        return self.tasks.filter(status='in_progress').count()

    def get_overdue_tasks_count(self):
        return self.tasks.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count()

    def get_tasks_due_today(self):
        today = timezone.now().date()
        return self.tasks.filter(
            due_date__date=today
        )

    def get_tasks_due_this_week(self):
        today = timezone.now().date()
        week_end = today + timedelta(days=7)
        return self.tasks.filter(
            due_date__date__range=[today, week_end]
        )

    def get_completion_rate(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        completed = self.get_completed_tasks_count()
        return (completed / total) * 100

    # Manager-specific methods
    def get_team_workload(self):
        """Returns workload distribution across team members."""
        if not self.is_manager():
            return None

        employees = self.employees.all()
        workload_data = []

        for employee in employees:
            pending_tasks = employee.get_pending_tasks_count()
            in_progress_tasks = employee.get_in_progress_tasks_count()

            workload_data.append({
                'employee': employee,
                'pending_tasks': pending_tasks,
                'in_progress_tasks': in_progress_tasks,
                'total_active_tasks': pending_tasks + in_progress_tasks
            })

        return workload_data

    def get_employee_performance(self):
        """Returns performance metrics for employees (for managers)."""
        if not self.is_manager():
            return None

        employees = self.employees.all()
        performance_data = []

        for employee in employees:
            total_tasks = employee.tasks.count()
            completed_tasks = employee.get_completed_tasks_count()
            overdue_tasks = employee.get_overdue_tasks_count()

            completion_rate = 0
            if total_tasks > 0:
                completion_rate = (completed_tasks / total_tasks) * 100

            performance_data.append({
                'employee': employee,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'overdue_tasks': overdue_tasks,
                'completion_rate': completion_rate
            })

        return performance_data