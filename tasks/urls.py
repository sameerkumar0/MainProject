from django.urls import path
from .views import (
    TaskListView, TaskCreateView, TaskUpdateStatusView, TaskDetailView,
    TaskAssignmentListView, TaskProgressListCreateView,
    task_create, task_list, task_assignment_page, employee_dashboard,
    EmployeeDashboardAPIView,
    ManagerDashboardAPIView,
    NotificationListView, NotificationMarkReadView,
    UserActivityListView,)

urlpatterns = [
    # Task views
    path('tasks/', TaskListView.as_view(), name='task-list'),  # List all tasks
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),  # Get task details
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),  # Create a task
    path('tasks/update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),  # Update task status

    # Task assignment views
    path('task-assignments/', TaskAssignmentListView.as_view(), name='task-assignment-list'),  # List/create assignments
    path('task_assign/', task_assignment_page, name='task-assignment-page'),  # Template view

    # Task progress views
    path('tasks/<int:task_id>/progress/', TaskProgressListCreateView.as_view(), name='task-progress-list'),  # List/create progress

    # Dashboard API views
    path('employee/dashboard/', EmployeeDashboardAPIView.as_view(), name='employee-dashboard-api'),  # Employee dashboard API
    path('manager/dashboard/', ManagerDashboardAPIView.as_view(), name='manager-dashboard-api'),  # Manager dashboard API

    # Dashboard utility API views
    path('notifications/', NotificationListView.as_view(), name='notification-list'),  # Notifications list/create
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),  # Mark notification as read
    path('activities/', UserActivityListView.as_view(), name='user-activity-list'),  # User activities list
    # Dashboard template views
    path('employee_dashboard/', employee_dashboard, name='employee-dashboard-legacy'),  # Legacy employee dashboard

    # Template views
    path('task_list/', task_list, name='task_list'),  # Template view
    path('task_create/', task_create, name='create-task'),  # Template view
]