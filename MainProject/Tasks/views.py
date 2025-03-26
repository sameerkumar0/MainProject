from rest_framework import generics, permissions
from .models import Task, ImprovementRequest
from .serializers import TaskSerializer, ImprovementRequestSerializer
from rest_framework.response import Response
from Users.permissions import IsManager, IsEmployee, IsClient

# List and Create Tasks (only managers can create tasks)
class TaskListCreateView(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role != 'manager':
            raise permissions.PermissionDenied("Only managers can create tasks.")
        serializer.save(created_by=self.request.user)

# Retrieve, Update, or Delete a Task
class TaskRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        # Only the assigned employee can update the task status
        if request.user.role == 'employee' and task.assigned_to != request.user:
            raise permissions.PermissionDenied("You cannot update this task.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only managers can delete tasks
        if request.user.role != 'manager':
            raise permissions.PermissionDenied("Only managers can delete tasks.")
        return super().destroy(request, *args, **kwargs)

# Improvement Request: Clients request improvements for a task
class ImprovementRequestCreateView(generics.CreateAPIView):
    queryset = ImprovementRequest.objects.all()
    serializer_class = ImprovementRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsClient]

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

# Manager resolves improvement requests
class ImprovementRequestResolveView(generics.UpdateAPIView):
    queryset = ImprovementRequest.objects.all()
    serializer_class = ImprovementRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def update(self, request, *args, **kwargs):
        improvement = self.get_object()
        improvement.status = 'resolved'
        improvement.save()
        serializer = self.get_serializer(improvement)
        return Response(serializer.data)
