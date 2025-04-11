from rest_framework import serializers
from .models import Task, TaskAssignment, TaskProgress, Notification, UserActivity
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

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
                  'start_date', 'completed_at', 'tags', 'time_remaining']
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
    user_name = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='related_task.title', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'user_name', 'notification_type', 'title', 'message',
                 'related_task', 'task_title', 'created_at', 'read']
        read_only_fields = ['created_at']


class UserActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='related_task.title', read_only=True)

    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'user_name', 'activity_type', 'description',
                 'related_task', 'task_title', 'created_at']
        read_only_fields = ['created_at']


class TaskMetricsSerializer(serializers.Serializer):
    """Serializer for task metrics shown on the dashboard."""
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()
    due_today = serializers.IntegerField()
    due_this_week = serializers.IntegerField()
    completion_rate = serializers.FloatField()


class CalendarTaskSerializer(serializers.ModelSerializer):
    """Serializer for tasks shown in the calendar view."""
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'status', 'priority', 'due_date', 'progress', 'assigned_to_name']


class EmployeeDashboardSerializer(serializers.Serializer):
    """Main serializer for the employee dashboard."""
    user = serializers.DictField()
    metrics = TaskMetricsSerializer()
    priority_tasks = TaskSerializer(many=True)
    recent_activities = UserActivitySerializer(many=True)
    recent_progress = TaskProgressSerializer(many=True)
    calendar_tasks = serializers.DictField(child=CalendarTaskSerializer(many=True))
    recent_notifications = NotificationSerializer(many=True)
    all_tasks = TaskSerializer(many=True, required=False)  # Added all tasks field


class EmployeePerformanceSerializer(serializers.Serializer):
    """Serializer for employee performance metrics."""
    employee = UserSerializer()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    average_completion_time = serializers.FloatField(required=False)


class EmployeeWorkloadSerializer(serializers.Serializer):
    """Serializer for employee workload metrics."""
    employee = UserSerializer()
    pending_tasks = serializers.IntegerField()
    in_progress_tasks = serializers.IntegerField()
    total_active_tasks = serializers.IntegerField()
    upcoming_deadlines = serializers.IntegerField()


class ManagerDashboardSerializer(serializers.Serializer):
    """Main serializer for the manager dashboard."""
    team_metrics = TaskMetricsSerializer()
    employee_performance = EmployeePerformanceSerializer(many=True)
    employee_workload = EmployeeWorkloadSerializer(many=True)
    unassigned_tasks = TaskSerializer(many=True)
    recent_activities = UserActivitySerializer(many=True)
    overdue_tasks = TaskSerializer(many=True)
    calendar_tasks = serializers.DictField(child=CalendarTaskSerializer(many=True))
