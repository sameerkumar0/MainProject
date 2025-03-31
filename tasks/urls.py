from django.urls import path
from .views import TaskListView,TaskCreateView, TaskUpdateStatusView, DocumentRequestView

urlpatterns = [
     path('tasks/', TaskListView.as_view(), name='task-list'),
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/update-status/', TaskUpdateStatusView.as_view(), name='task-update-status'),  # Employee can update status
    path('document-requests/', DocumentRequestView.as_view(), name='document-request'),  # Employee can request documents
]
