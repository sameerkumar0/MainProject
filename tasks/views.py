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
            queryset = Task.objects.all()  # Managers see all tasks
        else:
            # Employees see only tasks assigned to them via TaskAssignment
            queryset = Task.objects.filter(assignments__employee=user)

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


@login_required
def task_list(request):
    """Render the appropriate task list template based on user role."""
    user = request.user

    if user.role == 'Manager':
        return render(request, 'tasks/manager_task_list.html')
    else:  # Employee
        return render(request, 'tasks/employee_task_list.html')


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


class EmployeeDashboardAPIView(APIView):
    """
    API view that provides all data needed for the employee dashboard.
    Returns metrics, priority tasks, recent activities, and calendar data.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get all dashboard data for the current user.
        """
        user = request.user

        # Always use employee data
        if user.role == 'Employee':
            # For employees, use their own data
            employee = user
            # Get tasks assigned to this employee via TaskAssignment
            tasks = Task.objects.filter(assignments__employee=employee)
        else:
            # For managers, we need to find an employee to show
            # First, try to get the first employee managed by this manager
            from users.models import CustomUser
            employees = CustomUser.objects.filter(manager=user, role='Employee')

            if employees.exists():
                employee = employees.first()
                # Get tasks assigned to this employee via TaskAssignment
                tasks = Task.objects.filter(assignments__employee=employee)
            else:
                # If no employees are managed by this manager, use the manager's data
                employee = user
                tasks = Task.objects.filter(assigned_by=user)

        # Calculate metrics
        today = timezone.now().date()
        week_end = today + timedelta(days=7)

        total_tasks = tasks.count()
        pending_tasks = tasks.filter(status='pending').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        completed_tasks = tasks.filter(status='completed').count()
        overdue_tasks = tasks.filter(due_date__lt=today, status__in=['pending', 'in_progress']).count()
        due_today_tasks = tasks.filter(due_date__date=today).count()
        due_this_week_tasks = tasks.filter(due_date__date__range=[today, week_end]).count()

        # Calculate completion rate
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100

        metrics = {
            'total': total_tasks,
            'pending': pending_tasks,
            'in_progress': in_progress_tasks,
            'completed': completed_tasks,
            'overdue': overdue_tasks,
            'due_today': due_today_tasks,
            'due_this_week': due_this_week_tasks,
            'completion_rate': completion_rate
        }

        # Get priority tasks
        priority_tasks = tasks.filter(
            priority__in=['high', 'urgent'],
            status__in=['pending', 'in_progress']
        ).order_by('due_date')[:5]

        # Get recent activities for the employee
        user_activities = UserActivity.objects.filter(
            Q(user=employee) | Q(related_task__assigned_to=employee)
        ).order_by('-created_at')[:10]

        # Get recent progress updates for the employee
        recent_progress = TaskProgress.objects.filter(
            task__assigned_to=employee
        ).order_by('-created_at')[:5]

        # Get recent notifications for the employee
        recent_notifications = Notification.objects.filter(
            user=employee
        ).order_by('-created_at')[:5]

        # Prepare calendar data
        calendar_tasks = {}
        for task in tasks.filter(due_date__isnull=False):
            date_str = task.due_date.strftime('%Y-%m-%d')
            if date_str not in calendar_tasks:
                calendar_tasks[date_str] = []
            calendar_tasks[date_str].append(task)

        # Get employee profile data
        from users.serializers import EmployeeSerializer
        employee_data = EmployeeSerializer(employee).data

        # Get all tasks assigned to the employee
        from .serializers import TaskSerializer
        all_tasks = tasks.order_by('-due_date')
        all_tasks_serialized = TaskSerializer(all_tasks, many=True).data

        # Prepare response data
        dashboard_data = {
            'user': employee_data,
            'metrics': metrics,
            'priority_tasks': priority_tasks,
            'recent_activities': user_activities,
            'recent_progress': recent_progress,
            'calendar_tasks': calendar_tasks,
            'recent_notifications': recent_notifications,
            'all_tasks': all_tasks_serialized  # Add all tasks to the response
        }

        # Serialize the data
        serializer = EmployeeDashboardSerializer(dashboard_data)
        return Response(serializer.data)


def employee_dashboard(request):
    # Check if the user is authenticated via JWT
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    # If no Authorization header, check if user is authenticated via session
    if not auth_header and not request.user.is_authenticated:
        # Redirect to login page
        return redirect('employee_login')

    return render(request, 'employee_dashboard.html')


class ManagerDashboardView(View):
    """
    Template view for the manager dashboard.
    """
    template_name = 'manager_dashboard.html'

    def get(self, request):
        """
        Handle GET request for the manager dashboard template.
        """
        # Check if the user is authenticated via JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        # If no Authorization header, check if user is authenticated via session
        if not auth_header and not request.user.is_authenticated:
            # Redirect to login page
            return redirect('manager_login')

        # Get manager data
        manager = request.user

        # Get all tasks created by this manager
        manager_tasks = Task.objects.filter(assigned_by=manager)

        # Calculate team metrics
        today = timezone.now().date()
        week_end = today + timedelta(days=7)

        total_tasks = manager_tasks.count()
        pending_tasks = manager_tasks.filter(status='pending').count()
        in_progress_tasks = manager_tasks.filter(status='in_progress').count()
        completed_tasks = manager_tasks.filter(status='completed').count()
        overdue_tasks = manager_tasks.filter(due_date__lt=today, status__in=['pending', 'in_progress']).count()
        due_today_tasks = manager_tasks.filter(due_date__date=today).count()
        due_this_week_tasks = manager_tasks.filter(due_date__date__range=[today, week_end]).count()

        # Calculate completion rate
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100

        # Get employees managed by this manager
        employees = CustomUser.objects.filter(manager=manager)

        # Get unassigned tasks
        unassigned_tasks = Task.objects.filter(assigned_by=manager, assignments__isnull=True)

        # Get recent activities
        recent_activities = UserActivity.objects.filter(
            Q(user=manager) | Q(user__in=employees)
        ).order_by('-created_at')[:5]

        # Get overdue tasks
        overdue_task_list = manager_tasks.filter(
            due_date__lt=today,
            status__in=['pending', 'in_progress']
        ).order_by('due_date')[:5]

        context = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'due_today_tasks': due_today_tasks,
            'due_this_week_tasks': due_this_week_tasks,
            'completion_rate': round(completion_rate, 1),
            'employees': employees,
            'unassigned_tasks': unassigned_tasks,
            'recent_activities': recent_activities,
            'overdue_task_list': overdue_task_list
        }

        return render(request, self.template_name, context)


class ManagerDashboardAPIView(APIView):
    """
    API view that provides all data needed for the manager dashboard.
    Returns team metrics, employee performance, workload distribution, and unassigned tasks.
    """
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get(self, request):
        """
        Get all dashboard data for the current manager.
        """
        manager = request.user

        # Get employees managed by this manager
        employees = CustomUser.objects.filter(manager=manager)

        # Get all tasks created by this manager
        manager_tasks = Task.objects.filter(assigned_by=manager)

        # Calculate team metrics
        today = timezone.now().date()
        week_end = today + timedelta(days=7)

        total_tasks = manager_tasks.count()
        pending_tasks = manager_tasks.filter(status='pending').count()
        in_progress_tasks = manager_tasks.filter(status='in_progress').count()
        completed_tasks = manager_tasks.filter(status='completed').count()
        overdue_tasks = manager_tasks.filter(due_date__lt=today, status__in=['pending', 'in_progress']).count()
        due_today_tasks = manager_tasks.filter(due_date__date=today).count()
        due_this_week_tasks = manager_tasks.filter(due_date__date__range=[today, week_end]).count()

        # Calculate completion rate
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100

        team_metrics = {
            'total': total_tasks,
            'pending': pending_tasks,
            'in_progress': in_progress_tasks,
            'completed': completed_tasks,
            'overdue': overdue_tasks,
            'due_today': due_today_tasks,
            'due_this_week': due_this_week_tasks,
            'completion_rate': completion_rate
        }

        # Calculate employee performance metrics
        employee_performance = []
        for employee in employees:
            employee_tasks = Task.objects.filter(assigned_to=employee)
            total = employee_tasks.count()
            completed = employee_tasks.filter(status='completed').count()
            overdue = employee_tasks.filter(due_date__lt=today, status__in=['pending', 'in_progress']).count()

            # Calculate average completion time for completed tasks
            avg_completion_time = None
            completed_tasks_with_dates = employee_tasks.filter(
                status='completed',
                start_date__isnull=False,
                completed_at__isnull=False
            )

            if completed_tasks_with_dates.exists():
                total_days = 0
                count = 0
                for task in completed_tasks_with_dates:
                    delta = task.completed_at - task.start_date
                    total_days += delta.total_seconds() / (60 * 60 * 24)  # Convert to days
                    count += 1
                if count > 0:
                    avg_completion_time = total_days / count

            # Calculate completion rate
            emp_completion_rate = 0
            if total > 0:
                emp_completion_rate = (completed / total) * 100

            employee_performance.append({
                'employee': employee,
                'total_tasks': total,
                'completed_tasks': completed,
                'overdue_tasks': overdue,
                'completion_rate': emp_completion_rate,
                'average_completion_time': avg_completion_time
            })

        # Calculate employee workload
        employee_workload = []
        for employee in employees:
            employee_tasks = Task.objects.filter(assigned_to=employee)
            pending = employee_tasks.filter(status='pending').count()
            in_progress = employee_tasks.filter(status='in_progress').count()
            upcoming_deadlines = employee_tasks.filter(
                due_date__date__range=[today, week_end],
                status__in=['pending', 'in_progress']
            ).count()

            employee_workload.append({
                'employee': employee,
                'pending_tasks': pending,
                'in_progress_tasks': in_progress,
                'total_active_tasks': pending + in_progress,
                'upcoming_deadlines': upcoming_deadlines
            })

        # Get unassigned tasks
        unassigned_tasks = Task.objects.filter(assigned_by=manager, assigned_to__isnull=True)

        # Get recent activities
        recent_activities = UserActivity.objects.filter(
            Q(user=manager) | Q(user__in=employees)
        ).order_by('-created_at')[:10]

        # Get overdue tasks
        overdue_task_list = manager_tasks.filter(
            due_date__lt=today,
            status__in=['pending', 'in_progress']
        ).order_by('due_date')[:10]

        # Prepare calendar data
        calendar_tasks = {}
        for task in manager_tasks.filter(due_date__isnull=False):
            date_str = task.due_date.strftime('%Y-%m-%d')
            if date_str not in calendar_tasks:
                calendar_tasks[date_str] = []
            calendar_tasks[date_str].append(task)

        # Prepare response data
        dashboard_data = {
            'team_metrics': team_metrics,
            'employee_performance': employee_performance,
            'employee_workload': employee_workload,
            'unassigned_tasks': unassigned_tasks,
            'recent_activities': recent_activities,
            'overdue_tasks': overdue_task_list,
            'calendar_tasks': calendar_tasks
        }

        # Serialize the data
        serializer = ManagerDashboardSerializer(dashboard_data)
        return Response(serializer.data)


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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_manager():
            # Managers see their own activities and their employees' activities
            return UserActivity.objects.filter(
                Q(user=user) | Q(user__manager=user)
            ).order_by('-created_at')
        else:
            # Employees see only their own activities
            return UserActivity.objects.filter(user=user).order_by('-created_at')



