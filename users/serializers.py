from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models import Count, Q
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

    def validate_email(self, value):
        # Basic email format validation
        if not value or '@' not in value:
            raise serializers.ValidationError("Please enter a valid email address.")

        # Check for common email domains
        common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        domain = value.split('@')[-1].lower()

        if domain not in common_domains and not domain.endswith('.edu') and not domain.endswith('.org') and not domain.endswith('.gov'):
            # Just a warning, not an error - we'll still process it
            print(f"Uncommon email domain: {domain} for {value}")

        return value


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        # Basic email format validation
        if not value or '@' not in value:
            raise serializers.ValidationError("Please enter a valid email address.")
        return value

    def validate_otp(self, value):
        # Validate OTP format
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value

    def validate_password(self, value):
        # Password strength validation
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        # Check for at least one digit
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit.")

        # Check for at least one uppercase letter
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")

        # Check for at least one special character
        special_chars = "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~"
        if not any(char in special_chars for char in value):
            raise serializers.ValidationError("Password must contain at least one special character.")

        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class EmployeeListSerializer(serializers.ModelSerializer):
    """Serializer for listing employees with basic info and task counts."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    task_counts = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    assigned_tasks = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "first_name", "last_name", "email", "phone_number",
            "tech_stack", "department_name", "is_available", "availability_status",
            "profile_photo", "task_counts", "completion_rate", "assigned_tasks"
        ]

    def get_task_counts(self, obj):
        from tasks.models import Task
        # Use the correct related name 'task_assignments' instead of 'tasks'
        return {
            "total": Task.objects.filter(assignments__employee=obj).count(),
            "pending": obj.get_pending_tasks_count(),
            "in_progress": obj.get_in_progress_tasks_count(),
            "completed": obj.get_completed_tasks_count(),
            "overdue": obj.get_overdue_tasks_count()
        }

    def get_completion_rate(self, obj):
        return obj.get_completion_rate()

    def get_assigned_tasks(self, obj):
        from tasks.models import Task

        # Get tasks assigned to this employee
        tasks = Task.objects.filter(assignments__employee=obj)

        # Return simplified task data
        return [{
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority,
            'due_date': task.due_date
        } for task in tasks]


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

        from tasks.models import Task
        for employee in obj.employees.all():
            # Use the correct query with assignments__employee instead of tasks
            team_tasks["total"] += Task.objects.filter(assignments__employee=employee).count()
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


class ManagerDashboardSerializer(serializers.Serializer):
    """Serializer for the manager dashboard data.
    Provides manager profile information, team statistics, and employee list with their tech stacks.
    """
    # Manager profile information
    user_id = serializers.IntegerField(source='id')
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    profile_photo = serializers.ImageField(read_only=True)
    department = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    # Team statistics
    team_size = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    in_progress_tasks = serializers.SerializerMethodField()
    pending_tasks = serializers.SerializerMethodField()
    overdue_tasks = serializers.SerializerMethodField()

    # Employee data
    employees = serializers.SerializerMethodField()
    unassigned_tasks = serializers.SerializerMethodField()
    recent_activities = serializers.SerializerMethodField()

    def get_team_size(self, manager):
        return CustomUser.objects.filter(role=UserRoles.EMPLOYEE).count()

    def get_total_tasks(self, manager):
        from tasks.models import Task
        return Task.objects.filter(assigned_by=manager).count()

    def get_completed_tasks(self, manager):
        from tasks.models import Task
        return Task.objects.filter(assigned_by=manager, status='completed').count()

    def get_in_progress_tasks(self, manager):
        from tasks.models import Task
        return Task.objects.filter(assigned_by=manager, status='in_progress').count()

    def get_pending_tasks(self, manager):
        from tasks.models import Task
        return Task.objects.filter(assigned_by=manager, status__in=['pending', 'assigned']).count()

    def get_overdue_tasks(self, manager):
        from tasks.models import Task
        from django.utils import timezone
        return Task.objects.filter(
            assigned_by=manager,
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress', 'assigned']
        ).count()

    def get_employees(self, manager):
        # Get all employees with optimized query
        from django.db.models import Count, Q
        from tasks.models import Task, TaskAssignment

        # Get all employees with optimized query
        employees = CustomUser.objects.filter(role=UserRoles.EMPLOYEE).prefetch_related(
            'task_assignments'  # Prefetch assignments using the correct related_name
        )

        # Use the optimized serializer
        return EmployeeListSerializer(employees, many=True, context={'manager': manager}).data

    def get_unassigned_tasks(self, manager):
        from tasks.models import Task, TaskAssignment
        from tasks.serializers import TaskSerializer

        # Get tasks created by this manager that have no assignments
        unassigned_tasks = Task.objects.filter(
            assigned_by=manager
        ).exclude(
            id__in=TaskAssignment.objects.values_list('task_id', flat=True)
        ).select_related('assigned_by')

        return TaskSerializer(unassigned_tasks, many=True).data

    def get_recent_activities(self, manager):
        from tasks.models import UserActivity
        from tasks.serializers import UserActivitySerializer

        # Get recent activities related to this manager's tasks
        recent_activities = UserActivity.objects.filter(
            Q(user=manager) | Q(related_task__assigned_by=manager)
        ).order_by('-created_at')[:10]

        return UserActivitySerializer(recent_activities, many=True).data


class TopPerformerSerializer(serializers.ModelSerializer):
    """Serializer for displaying top performing employees."""
    completion_rate = serializers.FloatField()
    completed_tasks = serializers.IntegerField()
    total_tasks = serializers.IntegerField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'profile_photo',
            'tech_stack', 'completion_rate', 'completed_tasks', 'total_tasks'
        ]


class EmployeeTasksSerializer(serializers.ModelSerializer):
    """Serializer for displaying employees with their assigned tasks."""
    tasks = serializers.SerializerMethodField()
    task_counts = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    completion_rate = serializers.SerializerMethodField()
    last_active_formatted = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'tech_stack', 'profile_photo', 'tasks', 'task_counts',
            'department_name', 'completion_rate', 'is_available',
            'availability_status', 'last_active_formatted', 'phone_number'
        ]

    def get_tasks(self, employee):
        from tasks.models import Task
        from tasks.serializers import TaskSerializer

        # Get tasks assigned to this employee with optimized query
        tasks = Task.objects.filter(assignments__employee=employee)\
            .select_related('assigned_by')\
            .prefetch_related('progress_updates')\
            .order_by('-due_date')

        return TaskSerializer(tasks, many=True).data

    def get_task_counts(self, employee):
        from tasks.models import Task

        # Use a single query with annotations for better performance
        tasks = Task.objects.filter(assignments__employee=employee)

        return {
            'total': tasks.count(),
            'completed': tasks.filter(status='completed').count(),
            'in_progress': tasks.filter(status='in_progress').count(),
            'pending': tasks.filter(status__in=['pending', 'assigned']).count(),
            'overdue': tasks.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress', 'assigned']
            ).count()
        }

    def get_completion_rate(self, employee):
        # Calculate task completion rate
        return employee.get_completion_rate()

    def get_last_active_formatted(self, employee):
        # Format last active time in a human-readable format
        if not employee.last_active:
            return 'Never'

        # Calculate time difference
        now = timezone.now()
        diff = now - employee.last_active

        if diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"