"""URL configuration for tasks app API endpoints."""
from django.urls import path
from .views import (
    # Task API views
    TaskListView, TaskCreateView, TaskUpdateStatusView, TaskDetailView,
    TaskProgressListCreateView, TaskAssignView,
    # Dashboard API views
    EmployeeDashboardAPIView, ManagerDashboardAPIView,
    # Utility API views
    NotificationListView, NotificationMarkReadView, UserActivityListView
)

urlpatterns = [
    # Task API endpoints
    path('', TaskListView.as_view(), name='task-list'),
    path('<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('create/', TaskCreateView.as_view(), name='task-create'),
    path('update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),
    path('assign/', TaskAssignView.as_view(), name='task-assign'),
    path('<int:task_id>/progress/', TaskProgressListCreateView.as_view(), name='task-progress-list'),

    # Dashboard API endpoints
    path('dashboard/employee/', EmployeeDashboardAPIView.as_view(), name='employee-dashboard-api'),
    path('dashboard/manager/', ManagerDashboardAPIView.as_view(), name='manager-dashboard-api'),

    # Utility API endpoints
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('activities/', UserActivityListView.as_view(), name='user-activity-list'),
]