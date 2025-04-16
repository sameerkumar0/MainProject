from rest_framework import serializers
from .models import Task, TaskAssignment, TaskProgress, Notification, UserActivity
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.username", read_only=True)
    document = serializers.FileField(required=False)
    days_remaining = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)
    time_remaining = serializers.CharField(source='get_time_remaining', read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='Employee'), required=False)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'assigned_to', 'assigned_to_name',
                  'assigned_by', 'assigned_by_name', 'status', 'priority', 'document',
                  'created_at', 'due_date', 'assigned_at', 'progress', 'days_remaining', 'is_overdue',
                  'start_date', 'completed_at', 'time_remaining']
        read_only_fields = ['assigned_by', 'created_at', 'progress', 'assigned_at', 'start_date', 'completed_at']

    def validate(self, data):
        # Ensure assigned_to is only set when status is 'assigned' (this logic is optional, but you can enforce it)
        if 'assigned_to' in data and data['assigned_to'] is None:
            raise serializers.ValidationError("Assigned employee must be specified for assignment.")

        # Check for duplicate tasks
        request = self.context.get('request')
        if request and request.method == 'POST':
            title = data.get('title')
            description = data.get('description')

            # Check if a task with the same title and description already exists for this manager
            existing_tasks = Task.objects.filter(
                title=title,
                description=description,
                assigned_by=request.user
            )

            if existing_tasks.exists():
                raise serializers.ValidationError({
                    'non_field_errors': [
                        'A task with this title and description already exists. Please create a different task.'
                    ]
                })

        return data



    def create(self, validated_data):
        # Handle task creation (manager will be set as the creator)
        task = super().create(validated_data)

        # Use the context to assign the manager (creator) to the task
        task.assigned_by = self.context['request'].user
        task.save()
        return task





class TaskDetailSerializer(TaskSerializer):
    progress_updates = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['progress_updates', 'assignments']

    def get_progress_updates(self, obj):
        updates = obj.progress_updates.all()[:3]  # Get the 3 most recent updates
        return TaskProgressSerializer(updates, many=True).data




class TaskProgressSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)

    class Meta:
        model = TaskProgress
        fields = ['id', 'task', 'task_title', 'updated_by', 'updated_by_name', 'progress_percentage',
                 'notes', 'created_at', 'time_spent', 'status_change']
        read_only_fields = ['created_at', 'status_change']


class NotificationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='related_task.title', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'username', 'notification_type', 'title', 'message',
                 'related_task', 'task_title', 'created_at', 'read']
        read_only_fields = ['created_at']


class UserActivitySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='related_task.title', read_only=True)

    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'username', 'activity_type', 'description',
                 'related_task', 'task_title', 'created_at']
        read_only_fields = ['created_at']


class DashboardSerializer(serializers.Serializer):
    """Serializer for the employee dashboard data.
    Provides user profile information, task statistics, and assigned tasks.
    """
    # User profile information
    user_id = serializers.IntegerField(source='id')
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    profile_photo = serializers.ImageField(read_only=True)
    tech_stack = serializers.CharField(allow_null=True, required=False)

    # Task statistics
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)

    # Tasks data
    assigned_tasks = serializers.SerializerMethodField()

    def get_assigned_tasks(self, user):
        # Get tasks assigned to the user
        tasks = Task.objects.filter(
            assignments__employee=user
        ).select_related('assigned_by').order_by('due_date')

        return TaskSerializer(tasks, many=True).data

    def to_representation(self, instance):
        # Get the base representation
        data = super().to_representation(instance)

        # Calculate task statistics
        tasks = Task.objects.filter(assignments__employee=instance)
        data['total_tasks'] = tasks.count()
        data['completed_tasks'] = tasks.filter(status='completed').count()
        data['in_progress_tasks'] = tasks.filter(status='in_progress').count()
        data['pending_tasks'] = tasks.filter(status__in=['pending', 'assigned']).count()
        data['overdue_tasks'] = tasks.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count()

        return data

