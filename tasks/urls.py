from django.urls import path
from .views import (
    TaskListView, TaskCreateView, TaskUpdateStatusView, TaskDetailView,
    TaskAssignmentListView, TaskProgressListCreateView,
    task_create, task_list
)

urlpatterns = [
    # Task views
    path('tasks/', TaskListView.as_view(), name='task-list'),  # List all tasks
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),  # Get task details
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),  # Create a task
    path('tasks/update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),  # Update task status

    # Task assignment views
    path('task-assignments/', TaskAssignmentListView.as_view(), name='task-assignment-list'),  # List/create assignments

    # Task progress views
    path('tasks/<int:task_id>/progress/', TaskProgressListCreateView.as_view(), name='task-progress-list'),  # List/create progress

    # Template views
    path('task_list/', task_list, name='task_list'),  # Template view
    path('task_create/', task_create, name='create-task'),  # Template view
]