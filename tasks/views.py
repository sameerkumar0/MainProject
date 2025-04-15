from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import Task, TaskAssignment, TaskProgress, Notification, UserActivity
from .serializers import *
from .permissions import IsManager, IsEmployee,IsTaskAssignedToEmployee
from notifications.email_services import send_email_notification
from django.db import transaction
from django.shortcuts import render, redirect
from rest_framework.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from rest_framework.views import View
from django.http import HttpResponseForbidden, JsonResponse
from rest_framework.permissions import IsAuthenticated

# Task Creation View (Separate)
class TaskCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated,IsManager]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        data['assigned_by'] = request.user.id  # Automatically set the manager (creator)
        serializer = TaskSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            task = serializer.save(assigned_by=request.user)
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def task_create(request):
    if request.user.role != 'Manager':
        return HttpResponseForbidden("You are not authorized to create tasks.")

    return render(request, 'tasks/task_create.html')

# Task Assignment View (Separate)
class TaskAssignView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request, *args, **kwargs):
        task_id = request.data.get('task_id')
        employee_id = request.data.get('employee_id')

        if not task_id or not employee_id:
            return Response({"error": "Both task_id and employee_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = Task.objects.get(id=task_id)
            employee = User.objects.get(id=employee_id, role='Employee')

            # Check if task is already assigned
            if TaskAssignment.objects.filter(task=task).exists():
                return Response({"error": "This task is already assigned"}, status=status.HTTP_400_BAD_REQUEST)

            # Create task assignment
            assignment = TaskAssignment.objects.create(
                task=task,
                employee=employee
            )

            # Update task status
            task.status = 'assigned'
            task.save()

            # Create notification for the employee
            Notification.objects.create(
                user=employee,
                notification_type='task_assigned',
                title='New Task Assigned',
                message=f'You have been assigned a new task: {task.title}',
                related_task=task
            )

            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                activity_type='task_assigned',
                description=f'Assigned task "{task.title}" to {employee.username}',
                related_task=task
            )

            return Response({
                "success": True,
                "message": f"Task '{task.title}' assigned to {employee.username}",
                "task_id": task.id,
                "employee_id": employee.id,
                "assigned_at": assignment.assigned_at
            }, status=status.HTTP_201_CREATED)

        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
            # Managers see all tasks with optimized query
            queryset = Task.objects.select_related('assigned_by').all()
        else:
            # Employees see only tasks assigned to them via TaskAssignment with optimized query
            queryset = Task.objects.select_related('assigned_by').prefetch_related(
                'assignments'
            ).filter(assignments__employee=user)

        # Apply filters using a single query where possible
        filter_params = {}

        # Filter by status if provided
        status_param = self.request.query_params.get('status', None)
        if status_param:
            filter_params['status'] = status_param

        # Filter by priority if provided
        priority_param = self.request.query_params.get('priority', None)
        if priority_param:
            filter_params['priority'] = priority_param

        # Filter by due date range
        due_date_from = self.request.query_params.get('due_date_from', None)
        if due_date_from:
            filter_params['due_date__gte'] = due_date_from

        due_date_to = self.request.query_params.get('due_date_to', None)
        if due_date_to:
            filter_params['due_date__lte'] = due_date_to

        # Apply all filters at once if any exist
        if filter_params:
            queryset = queryset.filter(**filter_params)

        # Filter overdue tasks (needs separate filter due to complex condition)
        overdue = self.request.query_params.get('overdue', None)
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress'])

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Get task statistics
        if request.user.role != 'Manager':
            total_tasks = queryset.count()
            completed_tasks = queryset.filter(status='completed').count()
            in_progress_tasks = queryset.filter(status='in_progress').count()
            pending_tasks = queryset.filter(status__in=['pending', 'assigned']).count()

            # Include statistics in response
            task_stats = {
                'total': total_tasks,
                'completed': completed_tasks,
                'in_progress': in_progress_tasks,
                'pending': pending_tasks
            }
        else:
            task_stats = None

        # Paginate if needed
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            if task_stats:
                response.data['task_stats'] = task_stats
            return response

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'results': serializer.data
        }
        if task_stats:
            response_data['task_stats'] = task_stats

        return Response(response_data)


@login_required
def task_list(request):
    """Render the appropriate task list template based on user role."""
    user = request.user

    if user.role == 'Manager':
        # For managers, show all tasks
        return render(request, 'tasks/manager_task_list.html')
    else:  # Employee
        # Get tasks assigned to the employee via TaskAssignment
        tasks = Task.objects.filter(assignments__employee=user)

        # Calculate task statistics
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        pending_tasks = tasks.filter(status__in=['pending', 'assigned']).count()

        # Prepare context for the template
        context = {
            'employee': user,
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'in_progress': in_progress_tasks,
                'pending': pending_tasks
            }
        }

        return render(request, 'tasks/employee_task_list.html', context)


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
        # For employees, return tasks assigned to them via TaskAssignment
        return Task.objects.filter(assignments__employee=user, assignments__completed_at__isnull=True)

def task_detail(request, pk):
    return render(request,'tasks/task_view.html')


def task_assign(request):
    """View for the task assignment page with modal."""
    if request.method == 'POST':
        # Handle the AJAX request
        try:
            import json
            data = json.loads(request.body)
            task_id = data.get('task_id')
            employee_id = data.get('employee_id')
            due_date = data.get('due_date')
            note = data.get('note')

            if not task_id or not employee_id:
                return JsonResponse({"error": "Both task and employee are required"}, status=400)

            # Get the task and employee
            task = Task.objects.get(id=task_id)
            employee = CustomUser.objects.get(id=employee_id, role='Employee')

            # Check if task is already assigned
            if TaskAssignment.objects.filter(task=task).exists():
                return JsonResponse({"error": "This task is already assigned"}, status=400)

            # Create task assignment
            assignment = TaskAssignment.objects.create(
                task=task,
                employee=employee
            )

            # Update task status and due date
            task.status = 'assigned'
            if due_date:
                from datetime import datetime
                task.due_date = datetime.strptime(due_date, '%Y-%m-%d')
            task.save()

            # Create notification for the employee
            Notification.objects.create(
                user=employee,
                notification_type='task_assigned',
                title='New Task Assigned',
                message=f'You have been assigned a new task: {task.title}',
                related_task=task
            )

            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                activity_type='task_assigned',
                description=f'Assigned task "{task.title}" to {employee.username}',
                related_task=task
            )

            return JsonResponse({
                "success": True,
                "message": f"Task '{task.title}' assigned to {employee.first_name} {employee.last_name}",
                "task_id": task.id,
                "employee_id": employee.id,
                "assigned_at": assignment.assigned_at.isoformat()
            })

        except Task.DoesNotExist:
            return JsonResponse({"error": "Task not found"}, status=404)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "Employee not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        # Get all unassigned tasks
        unassigned_tasks = Task.objects.filter(assignments__isnull=True)

        # Get all employees
        employees = CustomUser.objects.filter(role='Employee')

        context = {
            'tasks': unassigned_tasks,
            'employees': employees
        }

        return render(request, 'tasks/task_assign.html', context)


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

            # Check if the task is assigned to the current user
            assignment = TaskAssignment.objects.filter(
                task=task,
                employee=request.user,
                completed_at__isnull=True
            ).first()

            if not assignment:
                return Response({'error': 'Permission denied. This task is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)

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


class NotificationListView(generics.ListCreateAPIView):
    """
    List all notifications for the current user or create a new notification.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationMarkReadView(generics.UpdateAPIView):
    """
    Mark a notification as read.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)


class UserActivityListView(generics.ListAPIView):
    """
    List all activities for the current user.
    """
    serializer_class = UserActivitySerializer


# Dashboard API View
class EmployeeDashboardAPIView(generics.RetrieveAPIView):
    """
    API endpoint for retrieving employee dashboard data.
    Provides user profile information, task statistics, and assigned tasks.
    """
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated,IsEmployee]

    def get_object(self):
        # Return the current user as the object to be serialized
        return self.request.user


class UnassignedTasksView(generics.ListAPIView):
    """
    API endpoint for retrieving unassigned tasks.
    Only managers can access this endpoint.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get_queryset(self):
        # Get tasks that are not assigned to any employee
        return Task.objects.filter(assignments__isnull=True)


class EmployeeTaskListView(generics.ListAPIView):
    """
    Optimized API endpoint specifically for retrieving tasks assigned to the logged-in employee.
    Includes task statistics and supports filtering by status, priority, and due date.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployee]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['due_date', 'priority']

    def get_queryset(self):
        user = self.request.user

        # Get tasks assigned to the employee with optimized query
        queryset = Task.objects.select_related('assigned_by').prefetch_related(
            'assignments', 'progress_updates'
        ).filter(assignments__employee=user)

        # Apply filters using a single query
        filter_params = {}

        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            filter_params['status'] = status

        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            filter_params['priority'] = priority

        # Filter by due date (upcoming tasks)
        upcoming = self.request.query_params.get('upcoming', None)
        if upcoming and upcoming.lower() == 'true':
            # Tasks due in the next 7 days
            filter_params['due_date__lte'] = timezone.now() + timedelta(days=7)
            filter_params['due_date__gte'] = timezone.now()

        # Filter overdue tasks
        overdue = self.request.query_params.get('overdue', None)
        if overdue and overdue.lower() == 'true':
            return queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress', 'assigned'])

        # Apply all filters at once if any exist
        if filter_params:
            queryset = queryset.filter(**filter_params)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Calculate task statistics
        all_tasks = Task.objects.filter(assignments__employee=request.user)
        task_stats = {
            'total': all_tasks.count(),
            'completed': all_tasks.filter(status='completed').count(),
            'in_progress': all_tasks.filter(status='in_progress').count(),
            'pending': all_tasks.filter(status__in=['pending', 'assigned']).count(),
            'overdue': all_tasks.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress', 'assigned']).count(),
            'upcoming': all_tasks.filter(due_date__lte=timezone.now() + timedelta(days=7), due_date__gte=timezone.now()).count()
        }

        # Paginate if needed
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['task_stats'] = task_stats
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'task_stats': task_stats
        })

