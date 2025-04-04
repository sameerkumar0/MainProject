from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Task
from .serializers import TaskSerializer
from .permissions import IsManager, IsEmployee
from tasks.permissions import IsTaskAssignedToEmployee
from notifications.email_services import send_email_notification
from django.db import transaction
from django.shortcuts import render
from rest_framework.exceptions import ValidationError

class TaskCreateView(generics.CreateAPIView):
    """
    Only Managers can create new tasks and assign them to Employees.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def perform_create(self, serializer):
        user = self.request.user  # The logged-in manager
        
        # Get assigned_to user from request data
        assigned_to = serializer.validated_data.get("assigned_to")
        
        # Ensure assigned_to is an employee
        if not assigned_to or assigned_to.role != "employee":
            raise ValidationError({"assigned_to": "Tasks can only be assigned to employees."})

        with transaction.atomic():  # Ensures atomicity
            task = serializer.save(assigned_by=user)  # Assign task with manager info

            # Send email notification
            if assigned_to.email:
                send_email_notification(
                    recipient_email=assigned_to.email,
                    subject="New Task Assigned",
                    message=f"Dear {assigned_to.username},\n\n"
                            f"You have been assigned a new task: {task.title}.\n"
                            f"Description: {task.description}\n\n"
                            f"Best regards,\n{user.username}"
                )

def task_create(request):
    return render(request,'tasks/task_create.html') 

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
    

def task_list(request):
    return render(request,'tasks/task_list.html')


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
        
