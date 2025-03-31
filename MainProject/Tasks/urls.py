from django.urls import path
from .views import (
    TaskListCreateView, 
    TaskRetrieveUpdateDestroyView, 
    ImprovementRequestCreateView, 
    ImprovementRequestResolveView
)

urlpatterns = [
    path('', TaskListCreateView.as_view(), name='task-list-create'),
    path('<int:pk>/', TaskRetrieveUpdateDestroyView.as_view(), name='task-detail'),
    path('<int:task_id>/request_improvement/', ImprovementRequestCreateView.as_view(), name='improvement-request'),
    path('improvements/<int:pk>/resolve/', ImprovementRequestResolveView.as_view(), name='improvement-resolve'),
]
