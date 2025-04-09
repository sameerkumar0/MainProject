from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

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

    objects = CustomUserManager()  # Assign custom manager


    def is_manager(self):
        return self.role == UserRoles.MANAGER

    def is_employee(self):
        return self.role == UserRoles.EMPLOYEE