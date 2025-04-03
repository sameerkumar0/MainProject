from django.urls import path
from .views import TaskListView,TaskCreateView, TaskUpdateStatusView, DocumentRequestView

urlpatterns = [
    path('tasks/', TaskListView.as_view(), name='task-list'),  # Employee sees assigned tasks
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),  # Manager assigns tasks
    path('tasks/update/<int:pk>/', TaskUpdateStatusView.as_view(), name='task-update'),  # Employee updates task status
    path('document-requests/', DocumentRequestView.as_view(), name='document-requests'),  # Document request
]