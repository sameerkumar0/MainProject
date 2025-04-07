from rest_framework import serializers
from .models import Task, TaskAssignment, TaskComment, TaskProgress
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

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'assigned_to', 'assigned_to_name',
                  'assigned_by', 'assigned_by_name', 'status', 'priority', 'document',
                  'created_at', 'due_date', 'progress', 'days_remaining', 'is_overdue']
        read_only_fields = ['assigned_by', 'created_at', 'progress']

class TaskDetailSerializer(TaskSerializer):
    comments = serializers.SerializerMethodField()
    progress_updates = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['comments', 'progress_updates', 'assignments']

    def get_comments(self, obj):
        comments = obj.comments.all()[:5]  # Get the 5 most recent comments
        return TaskCommentSerializer(comments, many=True).data

    def get_progress_updates(self, obj):
        updates = obj.progress_updates.all()[:3]  # Get the 3 most recent updates
        return TaskProgressSerializer(updates, many=True).data

    def get_assignments(self, obj):
        assignments = obj.assignments.all()
        return TaskAssignmentSerializer(assignments, many=True).data

class TaskAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)

    class Meta:
        model = TaskAssignment
        fields = ['id', 'task', 'task_title', 'employee', 'employee_name', 'assigned_at',
                  'accepted', 'accepted_at', 'completed_at', 'estimated_hours', 'actual_hours']
        read_only_fields = ['assigned_at', 'accepted_at', 'completed_at']

class TaskCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'user', 'user_name', 'comment', 'created_at']
        read_only_fields = ['created_at']

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