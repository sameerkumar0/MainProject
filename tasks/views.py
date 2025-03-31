from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Task, DocumentRequest
from .serializers import TaskSerializer, DocumentRequestSerializer
from users.permissions import IsManager, IsEmployee
from tasks.permissions import IsTaskAssignedToEmployee
from notifications.email_services import send_email_notification
from django.db import transaction

class TaskCreateView(generics.CreateAPIView):
    """
    Only Managers can create new tasks.
    """
    serializer_class = TaskSerializer
    permission_classes = [ IsManager]

    def perform_create(self, serializer):
        user = self.request.user
        with transaction.atomic():  # Ensures atomicity
            task = serializer.save(assigned_by=user)
            send_email_notification(
                task.assigned_to.email,
                "New Task Assigned",
                f"You have been assigned a new task: {task.title}"
            )

class TaskListView(generics.ListAPIView):
    """
    Employees see only their tasks.
    Managers see all tasks.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            return Task.objects.all()  # Managers see all tasks
        return Task.objects.filter(assigned_to=user)

class TaskUpdateStatusView(generics.UpdateAPIView):
    """
    Employees can update only their assigned tasks.
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsEmployee, IsTaskAssignedToEmployee]

    def patch(self, request, *args, **kwargs):
        try:
            task = get_object_or_404(Task, pk=kwargs['pk'])

            if task.assigned_to != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            new_status = request.data.get('status')
            if new_status not in ['pending', 'in_progress', 'completed']:
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

            task.status = new_status
            task.save()
            send_email_notification(task.assigned_by.email, "Task Status Updated", f"Task '{task.title}' is now {task.status}")

            return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentRequestView(generics.ListCreateAPIView):
    """
    Employees can request documents for tasks they are assigned to.
    Managers can view all document requests.
    """
    queryset = DocumentRequest.objects.all()
    serializer_class = DocumentRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            if user.role == 'manager':
                return DocumentRequest.objects.all()  # Managers see all requests
            return DocumentRequest.objects.filter(requested_by=user)  # Employees see only their own requests
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        user = self.request.user
        try:
            task = serializer.validated_data.get('task')

            if task.assigned_to != user:
                return Response({'error': 'You can only request documents for your assigned tasks'}, status=status.HTTP_403_FORBIDDEN)

            serializer.save(requested_by=user)

        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
