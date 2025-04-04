from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.username", read_only=True)
    document = serializers.FileField(required=False)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'assigned_to', 'assigned_to_name', 
                  'assigned_by', 'assigned_by_name', 'status', 'document', 'created_at']
        read_only_fields = ['assigned_by', 'created_at']