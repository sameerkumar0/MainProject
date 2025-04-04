from django.urls import path
from .views import TaskListView,TaskCreateView, TaskUpdateStatusView,task_create,task_list

urlpatterns = [
    path('tasks/', TaskListView.as_view(), name='task-list'),  # Employee sees assigned tasks
    path('task_list/',task_list,name='task_list'),

    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),  # Manager assigns tasks
    path('task_create/',task_create,name='create-task'),
    path('tasks/update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),  # Employee updates task status
]