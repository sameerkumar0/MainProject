"""URL configuration for tasks app API endpoints."""
from django.urls import path
from .views import (
    # Task API views
    TaskListView, TaskCreateView, TaskUpdateStatusView, TaskDetailView,
    TaskProgressListCreateView, TaskAssignView, EmployeeTaskListView, UnassignedTasksView,
    # Utility API views
    NotificationListView, NotificationMarkReadView, UserActivityListView, user_activity_list,
    # Dashboard API views
    EmployeeDashboardAPIView
)

urlpatterns = [
    # Task API endpoints
    path('', TaskListView.as_view(), name='task-list'),
    path('employee/', EmployeeTaskListView.as_view(), name='employee-task-list'),
    path('employee/<int:employee_id>/tasks/', EmployeeTaskListView.as_view(), name='employee-specific-task-list'),
    path('unassigned/', UnassignedTasksView.as_view(), name='unassigned-tasks'),
    path('<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('create/', TaskCreateView.as_view(), name='task-create'),
    path('update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),
    path('assign/', TaskAssignView.as_view(), name='task-assign'),
    path('<int:task_id>/progress/', TaskProgressListCreateView.as_view(), name='task-progress-list'),

    # Utility API endpoints
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('activities/', UserActivityListView.as_view(), name='user-activity-list'),
    path('activities/view/', user_activity_list, name='user-activity-list-view'),

    # Dashboard API endpoints
    path('dashboard/', EmployeeDashboardAPIView.as_view(), name='employee-dashboard-api'),
]