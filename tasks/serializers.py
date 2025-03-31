from rest_framework import serializers
from .models import Task, DocumentRequest

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.username", read_only=True)
    document = serializers.FileField(required=False)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'assigned_to', 'assigned_to_name', 
                  'assigned_by', 'assigned_by_name', 'status', 'document', 'created_at']
        read_only_fields = ['assigned_by', 'created_at']

class DocumentRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = DocumentRequest
        fields = ['id', 'task', 'task_title', 'requested_by', 'requested_by_name', 'status']
        read_only_fields = ['requested_by']
