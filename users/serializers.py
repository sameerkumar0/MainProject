from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import CustomUser, UserRoles, Department
from django.contrib.auth import authenticate


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class EmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False)
    department_name = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    task_counts = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "first_name", "last_name", "username", "email", "password",
            "phone_number", "tech_stack", "department", "department_name", "manager", "manager_name",
            "is_available", "profile_photo", "last_active", "availability_status", "task_counts"
        ]
        read_only_fields = ["last_active"]

    def get_manager_name(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return None

    def get_task_counts(self, obj):
        from tasks.models import Task
        return {
            "total": Task.objects.filter(assignments__employee=obj).count(),
            "pending": obj.get_pending_tasks_count(),
            "in_progress": obj.get_in_progress_tasks_count(),
            "completed": obj.get_completed_tasks_count(),
            "overdue": obj.get_overdue_tasks_count()
        }

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])  # Hash password
        validated_data["role"] = UserRoles.EMPLOYEE  # Set role explicitly
        user = CustomUser.objects.create(**validated_data)
        return user

    def update(self, instance, validated_data):
        # Handle password updates separately
        password = validated_data.pop('password', None)
        if password:
            instance.password = make_password(password)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ManagerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username", "email", "password", "phone_number","profile_photo"]

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        validated_data["role"] = UserRoles.MANAGER
        user = CustomUser.objects.create(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise serializers.ValidationError("Username and password are required.")

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        data["user"] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class EmployeeListSerializer(serializers.ModelSerializer):
    """Serializer for listing employees with basic info and task counts."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    task_counts = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "first_name", "last_name", "email", "phone_number",
            "tech_stack", "department_name", "is_available", "availability_status",
            "profile_photo", "task_counts", "completion_rate"
        ]

    def get_task_counts(self, obj):
        return {
            "total": obj.tasks.count(),
            "pending": obj.get_pending_tasks_count(),
            "in_progress": obj.get_in_progress_tasks_count(),
            "completed": obj.get_completed_tasks_count(),
            "overdue": obj.get_overdue_tasks_count()
        }

    def get_completion_rate(self, obj):
        return obj.get_completion_rate()


class ManagerProfileSerializer(serializers.ModelSerializer):
    """Serializer for manager profile with team information."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_size = serializers.SerializerMethodField()
    team_task_counts = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "first_name", "last_name", "email", "phone_number",
            "profile_photo", "department", "department_name", "team_size", "team_task_counts"
        ]

    def get_team_size(self, obj):
        return obj.employees.count()

    def get_team_task_counts(self, obj):
        team_tasks = {
            "total": 0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "overdue": 0
        }

        for employee in obj.employees.all():
            team_tasks["total"] += employee.tasks.count()
            team_tasks["pending"] += employee.get_pending_tasks_count()
            team_tasks["in_progress"] += employee.get_in_progress_tasks_count()
            team_tasks["completed"] += employee.get_completed_tasks_count()
            team_tasks["overdue"] += employee.get_overdue_tasks_count()

        return team_tasks


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = CustomUser
        fields = [
            "first_name", "last_name", "email", "phone_number", "tech_stack",
            "profile_photo", "password", "availability_status", "is_available"
        ]

    def update(self, instance, validated_data):
        # Handle password updates separately
        password = validated_data.pop('password', None)
        if password:
            instance.password = make_password(password)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance