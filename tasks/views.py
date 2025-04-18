from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.db import transaction
from datetime import timedelta, datetime

from .models import Task, TaskAssignment, TaskProgress, Notification, UserActivity
from .serializers import *
from .permissions import IsManager, IsEmployee, IsTaskAssignedToEmployee
from notifications.email_services import send_email_notification
from users.models import CustomUser

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

            # Check if due_date is provided in the request
            due_date = request.data.get('due_date')
            if due_date:
                from datetime import datetime
                # Parse the date and make it timezone-aware
                naive_date = datetime.strptime(due_date, '%Y-%m-%d')
                # Set the time to end of day (23:59:59) in the current timezone
                aware_date = timezone.make_aware(
                    datetime.combine(naive_date.date(), datetime.max.time().replace(microsecond=0))
                )
                task.due_date = aware_date

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
    """Render the appropriate task list template based on user role and query parameters."""
    user = request.user

    # Check if an employee_id is provided in the query parameters (for managers viewing employee tasks)
    employee_id = request.GET.get('employee_id')

    if user.role == 'Manager' and employee_id:
        # Manager viewing a specific employee's tasks
        try:
            from users.models import CustomUser
            employee = CustomUser.objects.get(id=employee_id, role='Employee')

            # Get tasks assigned to the specified employee
            tasks = Task.objects.filter(assignments__employee=employee)

            # Calculate task statistics
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(status='completed').count()
            in_progress_tasks = tasks.filter(status='in_progress').count()
            pending_tasks = tasks.filter(status__in=['pending', 'assigned']).count()

            # Prepare context for the template
            context = {
                'employee': employee,
                'task_stats': {
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'in_progress': in_progress_tasks,
                    'pending': pending_tasks
                },
                'is_manager_view': True  # Flag to indicate this is a manager viewing employee tasks
            }

            return render(request, 'tasks/employee_task_list.html', context)

        except CustomUser.DoesNotExist:
            # If employee not found, redirect to all tasks
            from django.contrib import messages
            messages.error(request, "Employee not found.")
            return render(request, 'tasks/employee_task_list.html', {'error': 'Employee not found'})

    elif user.role == 'Manager':
        # For managers viewing all tasks
        tasks = Task.objects.all()

        # Calculate task statistics
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        pending_tasks = tasks.filter(status__in=['pending', 'assigned']).count()

        context = {
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'in_progress': in_progress_tasks,
                'pending': pending_tasks
            }
        }

        return render(request, 'tasks/employee_task_list.html', context)

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

@login_required
def task_detail(request, pk):
    """View for displaying task details with progress history."""
    try:
        # Get the task with related data
        task = Task.objects.select_related('assigned_by').get(pk=pk)

        # Check if user has permission to view this task
        user = request.user
        if user.role == 'Employee':
            # Employees can only view tasks assigned to them
            if not TaskAssignment.objects.filter(task=task, employee=user).exists():
                return HttpResponseForbidden("You don't have permission to view this task.")

        # Get progress updates for this task
        progress_updates = TaskProgress.objects.filter(task=task).select_related('updated_by').order_by('-created_at')

        # Handle progress update form submission
        if request.method == 'POST' and user.role == 'Employee':
            progress_percentage = request.POST.get('progress_percentage')
            notes = request.POST.get('notes', '')

            try:
                progress_percentage = int(progress_percentage)
                if 0 <= progress_percentage <= 100:
                    # Create progress update
                    TaskProgress.objects.create(
                        task=task,
                        updated_by=user,
                        progress_percentage=progress_percentage,
                        notes=notes
                    )

                    # Update task progress
                    task.progress = progress_percentage

                    # If progress is 100%, mark task as completed
                    if progress_percentage == 100:
                        task.status = 'completed'

                        # Update task assignment
                        assignment = TaskAssignment.objects.filter(task=task, employee=user).first()
                        if assignment and not assignment.completed_at:
                            assignment.completed_at = timezone.now()
                            assignment.save()

                    # If progress is > 0 and status is pending, change to in_progress
                    elif progress_percentage > 0 and task.status == 'pending':
                        task.status = 'in_progress'

                    task.save()

                    # Create notification for the manager
                    Notification.objects.create(
                        user=task.assigned_by,
                        notification_type='task_progress',
                        title='Task Progress Updated',
                        message=f'{user.first_name} {user.last_name} updated progress on task "{task.title}" to {progress_percentage}%',
                        related_task=task
                    )

                    # Create activity record
                    UserActivity.objects.create(
                        user=user,
                        activity_type='task_progress',
                        description=f'Updated progress on task "{task.title}" to {progress_percentage}%',
                        related_task=task
                    )

                    # Redirect to avoid form resubmission
                    return redirect('task_detail', pk=task.id)
                else:
                    # Handle invalid progress percentage
                    return render(request, 'tasks/task_view.html', {
                        'task': task,
                        'progress_updates': progress_updates,
                        'error': 'Progress must be between 0 and 100'
                    })
            except ValueError:
                # Handle non-numeric progress percentage
                return render(request, 'tasks/task_view.html', {
                    'task': task,
                    'progress_updates': progress_updates,
                    'error': 'Progress must be a number'
                })

        # Render the template with context
        return render(request, 'tasks/task_view.html', {
            'task': task,
            'progress_updates': progress_updates
        })

    except Task.DoesNotExist:
        # Handle task not found
        return render(request, 'tasks/task_view.html', {'error': 'Task not found'})


@login_required
def task_update_progress(request, pk):
    """View for handling task progress updates via form submission."""
    if request.method != 'POST':
        # Redirect to task detail page if not a POST request
        return redirect('task_detail', pk=pk)

    try:
        # Get the task
        task = get_object_or_404(Task, pk=pk)

        # Check if user has permission to update this task
        user = request.user
        if user.role != 'Employee':
            return HttpResponseForbidden("Only employees can update task progress.")

        # Check if task is assigned to this employee
        if not TaskAssignment.objects.filter(task=task, employee=user).exists():
            return HttpResponseForbidden("You can only update progress on tasks assigned to you.")

        # Get form data
        progress_percentage = request.POST.get('progress_percentage')
        notes = request.POST.get('notes', '')

        try:
            progress_percentage = int(progress_percentage)
            if 0 <= progress_percentage <= 100:
                # Create progress update
                TaskProgress.objects.create(
                    task=task,
                    updated_by=user,
                    progress_percentage=progress_percentage,
                    notes=notes
                )

                # Update task progress
                task.progress = progress_percentage

                # If progress is 100%, mark task as completed
                if progress_percentage == 100:
                    task.status = 'completed'

                    # Update task assignment
                    assignment = TaskAssignment.objects.filter(task=task, employee=user).first()
                    if assignment and not assignment.completed_at:
                        assignment.completed_at = timezone.now()
                        assignment.save()

                # If progress is > 0 and status is pending, change to in_progress
                elif progress_percentage > 0 and task.status in ['pending', 'assigned']:
                    task.status = 'in_progress'

                task.save()

                # Create notification for the manager
                Notification.objects.create(
                    user=task.assigned_by,
                    notification_type='task_progress',
                    title='Task Progress Updated',
                    message=f'{user.first_name} {user.last_name} updated progress on task "{task.title}" to {progress_percentage}%',
                    related_task=task
                )

                # Create activity record
                UserActivity.objects.create(
                    user=user,
                    activity_type='task_progress',
                    description=f'Updated progress on task "{task.title}" to {progress_percentage}%',
                    related_task=task
                )

                # Redirect to task detail page with success message
                return redirect('task_detail', pk=task.id)
            else:
                # Handle invalid progress percentage
                return render(request, 'tasks/task_view.html', {
                    'task': task,
                    'progress_updates': TaskProgress.objects.filter(task=task).select_related('updated_by').order_by('-created_at'),
                    'error': 'Progress must be between 0 and 100'
                })
        except ValueError:
            # Handle non-numeric progress percentage
            return render(request, 'tasks/task_view.html', {
                'task': task,
                'progress_updates': TaskProgress.objects.filter(task=task).select_related('updated_by').order_by('-created_at'),
                'error': 'Progress must be a number'
            })
    except Task.DoesNotExist:
        # Handle task not found
        return render(request, 'tasks/task_view.html', {'error': 'Task not found'})


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
                from django.utils import timezone
                from datetime import datetime
                # Parse the date and make it timezone-aware
                naive_date = datetime.strptime(due_date, '%Y-%m-%d')
                # Set the time to end of day (23:59:59) in the current timezone
                aware_date = timezone.make_aware(
                    datetime.combine(naive_date.date(), datetime.max.time().replace(microsecond=0))
                )
                task.due_date = aware_date
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        return TaskProgress.objects.filter(task_id=task_id)

    def create(self, request, *args, **kwargs):
        # Get task_id from URL
        task_id = self.kwargs.get('task_id')

        # Make a mutable copy of the request data
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        # If task is not in request data, add it
        if 'task' not in data:
            data['task'] = task_id

        # Add updated_by if not present
        if 'updated_by' not in data:
            data['updated_by'] = request.user.id

        # Remove status field if present (we'll handle it in perform_create)
        if 'status' in data:
            # Store it in the request for later use
            request.status_value = data.pop('status')

        # Update the request data
        request._full_data = data

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(Task, pk=task_id)

        # Check if user is associated with this task
        user = self.request.user

        # For employees, check if the task is assigned to them
        if user.role == 'Employee':
            if not TaskAssignment.objects.filter(task=task, employee=user).exists():
                raise ValidationError("You can only update progress on tasks assigned to you.")

        # Validate progress percentage
        progress_percentage = serializer.validated_data.get('progress_percentage')
        if not (0 <= progress_percentage <= 100):
            raise ValidationError("Progress percentage must be between 0 and 100.")

        # Get status if provided from the request
        status_value = getattr(self.request, 'status_value', None)

        # Create the progress update (without the status field)
        progress_update = serializer.save(task=task, updated_by=user)

        # Update task progress and status
        task.progress = progress_percentage

        # Update task status based on progress or explicit status
        if status_value:
            task.status = status_value
        elif progress_percentage == 100:
            task.status = 'completed'

            # Update task assignment if completed
            if user.role == 'Employee':
                assignment = TaskAssignment.objects.filter(task=task, employee=user).first()
                if assignment and not assignment.completed_at:
                    assignment.completed_at = timezone.now()
                    assignment.save()
        elif progress_percentage > 0 and task.status in ['pending', 'assigned']:
            task.status = 'in_progress'

        # Save the task
        task.save()


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
    Supports filtering by activity_type, user, and date range.
    """
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = UserActivitySerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'activity_type']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = UserActivity.objects.select_related('user', 'related_task')

        # Apply filters
        activity_type = self.request.query_params.get('activity_type', None)
        user_id = self.request.query_params.get('user', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)

        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to:
            # Add one day to include the end date
            date_to_end = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=date_to_end)

        return queryset


@login_required
def user_activity_list(request):
    """
    Render the user activity list template.
    Only managers can access this view.
    """
    if request.user.role != 'Manager':
        return HttpResponseForbidden("You are not authorized to view this page.")

    return render(request, 'tasks/user_activity_list.html')


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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        # Get tasks created by this manager that have no assignments
        manager = self.request.user

        # Use a more efficient query with select_related
        return Task.objects.filter(
            assigned_by=manager,
            assignments__isnull=True
        ).select_related('assigned_by')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Get task statistics
        total_unassigned = queryset.count()
        high_priority = queryset.filter(priority__in=['high', 'urgent']).count()

        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)

        # Return with statistics
        return Response({
            'results': serializer.data,
            'stats': {
                'total_unassigned': total_unassigned,
                'high_priority': high_priority
            }
        })


class EmployeeTaskListView(generics.ListAPIView):
    """
    Optimized API endpoint specifically for retrieving tasks assigned to the logged-in employee.
    Includes task statistics and supports filtering by status, priority, and due date.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['due_date', 'priority']

    def get_queryset(self):
        user = self.request.user
        employee_id = self.kwargs.get('employee_id', None)

        # If employee_id is provided and user is a manager, get tasks for that employee
        if employee_id and user.role == 'Manager':
            from users.models import CustomUser
            try:
                employee = CustomUser.objects.get(id=employee_id, role='Employee')
                queryset = Task.objects.select_related('assigned_by').prefetch_related(
                    'assignments', 'progress_updates'
                ).filter(assignments__employee=employee)
            except CustomUser.DoesNotExist:
                return Task.objects.none()
        # If user is an employee, get their tasks
        elif user.role == 'Employee':
            queryset = Task.objects.select_related('assigned_by').prefetch_related(
                'assignments', 'progress_updates'
            ).filter(assignments__employee=user)
        # If user is a manager and no employee_id is provided, get all tasks
        else:
            queryset = Task.objects.select_related('assigned_by').prefetch_related(
                'assignments', 'progress_updates'
            ).all()

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
        employee_id = self.kwargs.get('employee_id', None)

        if employee_id and request.user.role == 'Manager':
            # For managers viewing a specific employee's tasks
            from users.models import CustomUser
            try:
                employee = CustomUser.objects.get(id=employee_id, role='Employee')
                all_tasks = Task.objects.filter(assignments__employee=employee)
            except CustomUser.DoesNotExist:
                all_tasks = Task.objects.none()
        elif request.user.role == 'Employee':
            # For employees viewing their own tasks
            all_tasks = Task.objects.filter(assignments__employee=request.user)
        else:
            # For managers viewing all tasks
            all_tasks = Task.objects.all()

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

