from rest_framework import serializers
from .models import Task, ImprovementRequest

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class ImprovementRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImprovementRequest
        fields = '__all__'
