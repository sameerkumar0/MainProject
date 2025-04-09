from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Task, TaskAssignment, TaskProgress
from .serializers import (
    TaskSerializer, TaskDetailSerializer,TaskProgressSerializer,
    TaskAssignmentCreateSerializer
)
from .permissions import IsManager, IsEmployee
from tasks.permissions import IsTaskAssignedToEmployee
from notifications.email_services import send_email_notification
from django.db import transaction
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import View
from django.core.paginator import Paginator


class TaskCreateView(generics.CreateAPIView):
    """
    Managers can create tasks without assigning them immediately.
    Assignment will be handled by a separate API.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def perform_create(self, serializer):
        user = self.request.user  # The logged-in manager

        # Prevent assignment in this view
        if "assigned_to" in serializer.validated_data:
            raise ValidationError({"detail": "Do not assign an employee during task creation."})

        with transaction.atomic():
            task = serializer.save(assigned_by=user)

@login_required
def task_create(request):
    return render(request,'tasks/task_create.html')

class TaskListView(generics.ListAPIView):
    """
    Employees see only their tasks.
    Managers see all tasks.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = None

        if user.role == 'Manager':
            queryset = Task.objects.all()  # Managers see all tasks
        else:
            queryset = Task.objects.filter(assigned_to=user)

        # Filter by status if provided
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by priority if provided
        priority_param = self.request.query_params.get('priority', None)
        if priority_param:
            queryset = queryset.filter(priority=priority_param)

        # Filter by due date range
        due_date_from = self.request.query_params.get('due_date_from', None)
        due_date_to = self.request.query_params.get('due_date_to', None)

        if due_date_from:
            queryset = queryset.filter(due_date__gte=due_date_from)
        if due_date_to:
            queryset = queryset.filter(due_date__lte=due_date_to)

        # Filter overdue tasks
        overdue = self.request.query_params.get('overdue', None)
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress'])

        return queryset


def task_list(request):
    return render(request,'tasks/task_list.html')


class TaskDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a task.
    """
    queryset = Task.objects.all()
    serializer_class = TaskDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'Manager':
            return Task.objects.all()
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

            # Get progress percentage if provided
            progress_percentage = request.data.get('progress', None)

            with transaction.atomic():
                # Update task status
                task.status = new_status

                # Update progress if provided
                if progress_percentage is not None:
                    try:
                        progress_percentage = int(progress_percentage)
                        if 0 <= progress_percentage <= 100:
                            task.progress = progress_percentage

                            # Create progress update record
                            TaskProgress.objects.create(
                                task=task,
                                updated_by=request.user,
                                progress_percentage=progress_percentage,
                                notes=request.data.get('notes', '')
                            )
                        else:
                            return Response({'error': 'Progress must be between 0 and 100'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    except ValueError:
                        return Response({'error': 'Progress must be a number'},
                                        status=status.HTTP_400_BAD_REQUEST)

                # If status is completed, set progress to 100%
                if new_status == 'completed' and task.progress < 100:
                    task.progress = 100
                    TaskProgress.objects.create(
                        task=task,
                        updated_by=request.user,
                        progress_percentage=100,
                        notes="Task marked as completed"
                    )

                # If status is in_progress and progress is 0, set to 10%
                if new_status == 'in_progress' and task.progress == 0:
                    task.progress = 10
                    TaskProgress.objects.create(
                        task=task,
                        updated_by=request.user,
                        progress_percentage=10,
                        notes="Task started"
                    )

                task.save()

                # Update task assignment if status is completed
                if new_status == 'completed':
                    assignment = TaskAssignment.objects.filter(task=task, employee=request.user).first()
                    if assignment and not assignment.completed_at:
                        assignment.completed_at = timezone.now()
                        assignment.save()

            # Send email notification
            send_email_notification(
                to_email=task.assigned_by.email,
                subject="Task Status Updated",
                message=f"Task '{task.title}' is now {task.status} with {task.progress}% progress."
            )

            return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskAssignmentListView(generics.ListCreateAPIView):
    """
    List all task assignments or create a new one.
    """
    permission_classes = [permissions.IsAuthenticated,IsManager]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskAssignmentCreateSerializer
        return TaskAssignmentCreateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'Manager':
            return TaskAssignment.objects.filter(task__assigned_by=user)
        return TaskAssignment.objects.filter(employee=user)

    def perform_create(self, serializer):
        task = serializer.validated_data.get('task')
        if self.request.user.role != 'Manager' or task.assigned_by != self.request.user:
            raise PermissionDenied("Only the assigning manager can create assignments for their tasks.")
        serializer.save()

@login_required
def task_assignment_page(request):
    if request.user.role == 'Manager':
        assignments = TaskAssignment.objects.filter(task__assigned_by=request.user)
        tasks = Task.objects.filter(assigned_by=request.user)
        employees = CustomUser.objects.filter(role='Employee')
    else:
        assignments = TaskAssignment.objects.filter(employee=request.user)
        tasks = []
        employees = []

    return render(request, 'tasks/task_assign.html', {
        'assignments': assignments,
        'tasks': tasks,
        'employees': employees,
        'user': request.user
    })



class TaskProgressListCreateView(generics.ListCreateAPIView):
    """
    List all progress updates for a task or create a new progress update.
    """
    serializer_class = TaskProgressSerializer
    permission_classes = [permissions.IsAuthenticated,IsManager]

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        return TaskProgress.objects.filter(task_id=task_id)

    def perform_create(self, serializer):
        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(Task, pk=task_id)

        # Check if user is associated with this task
        user = self.request.user
        if user.role != 'Manager' and task.assigned_to != user:
            raise ValidationError("You can only update progress on tasks assigned to you.")

        # Validate progress percentage
        progress_percentage = serializer.validated_data.get('progress_percentage')
        if not (0 <= progress_percentage <= 100):
            raise ValidationError("Progress percentage must be between 0 and 100.")

        serializer.save(task=task, updated_by=user)



class EmployeeDashboardView(View):
    """
    View for the employee dashboard.
    Displays task overview, priority tasks, recent activity, and all tasks.
    """
    template_name = 'employee_dashboard.html'
    
    def get(self, request):
        """
        Handle GET request for the employee dashboard.
        Fetches all necessary data and renders the dashboard template.
        """
        # Get the current employee
        employee = request.user
        
        # Get all tasks assigned to this employee
        tasks = Task.objects.filter(assigned_to=employee)
        
        # Calculate task metrics
        total_tasks = tasks.count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        completed_tasks = tasks.filter(status='completed').count()
        pending_tasks = tasks.filter(status='pending').count()
        
        # Calculate overdue tasks
        today = timezone.now().date()
        overdue_tasks = tasks.filter(
            due_date__lt=today, 
            status__in=['pending', 'in_progress']
        ).count()
        
        # Get priority tasks (high priority or urgent, not completed)
        priority_tasks = tasks.filter(
            priority__in=['high', 'urgent'],
            status__in=['pending', 'in_progress']
        ).order_by('due_date')[:5]  # Limit to 5 tasks
        
        # Get recent activity (task updates, new assignments)
        recent_activities = []
        
        # Get task progress updates
        progress_updates = TaskProgress.objects.filter(
            task__assigned_to=employee
        ).order_by('-created_at')[:5]
        
        for update in progress_updates:
            recent_activities.append({
                'type': 'progress_update',
                'task': update.task,
                'progress': update.progress,
                'timestamp': update.created_at
            })
        
        # Get recent task assignments
        recent_assignments = tasks.order_by('-created_at')[:5]
        
        for task in recent_assignments:
            recent_activities.append({
                'type': 'assignment',
                'task': task,
                'timestamp': task.created_at
            })
        
        # Sort activities by timestamp
        recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activities = recent_activities[:5]  # Limit to 5 activities
        
        # Get all tasks with pagination
        paginator = Paginator(tasks.order_by('due_date'), 10)
        page = request.GET.get('page', 1)
        all_tasks = paginator.get_page(page)
        
        # Get task calendar data (tasks grouped by due date)
        calendar_data = {}
        
        for task in tasks:
            if task.due_date:
                date_str = task.due_date.strftime('%Y-%m-%d')
                if date_str not in calendar_data:
                    calendar_data[date_str] = []
                calendar_data[date_str].append(task)
        
        # Prepare context for the template
        context = {
            'employee': employee,
            'metrics': {
                'total': total_tasks,
                'in_progress': in_progress_tasks,
                'completed': completed_tasks,
                'pending': pending_tasks,
                'overdue': overdue_tasks
            },
            'priority_tasks': priority_tasks,
            'recent_activities': recent_activities,
            'all_tasks': all_tasks,
            'calendar_data': calendar_data
        }
        
        return render(request, self.template_name, context)


@login_required
def employee_dashboard(request):
    return render(request,'employee_dashboard.html')