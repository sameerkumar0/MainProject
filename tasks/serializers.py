from rest_framework import serializers
from .models import Task, TaskAssignment, TaskProgress
from django.contrib.auth import get_user_model

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

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'assigned_to', 'assigned_to_name',
                  'assigned_by', 'assigned_by_name', 'status', 'priority', 'document',
                  'created_at', 'due_date', 'assigned_at', 'progress', 'days_remaining', 'is_overdue']
        read_only_fields = ['assigned_by', 'created_at', 'progress', 'assigned_at']


class TaskTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title']


class TaskDetailSerializer(TaskSerializer):
    progress_updates = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['progress_updates', 'assignments']

    def get_progress_updates(self, obj):
        updates = obj.progress_updates.all()[:3]  # Get the 3 most recent updates
        return TaskProgressSerializer(updates, many=True).data

    def get_assignments(self, obj):
        assignments = obj.assignments.all()
        return TaskAssignmentCreateSerializer(assignments, many=True).data




class TaskProgressSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = TaskProgress
        fields = ['id', 'task', 'updated_by', 'updated_by_name', 'progress_percentage', 'notes', 'created_at']
        read_only_fields = ['created_at']


class TaskAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = ['task', 'employee', 'estimated_hours']

    def validate(self, data):
        # Check if this task is already assigned to this employee
        if TaskAssignment.objects.filter(task=data['task'], employee=data['employee']).exists():
            raise serializers.ValidationError("This task is already assigned to this employee.")
        return data
