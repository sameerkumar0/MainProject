"""
URL configuration for tasks app web views.
"""
from django.urls import path
from .views import (
    task_create, task_list, task_detail,
    employee_dashboard, ManagerDashboardView
)

urlpatterns = [
    # Dashboard views
    path('', ManagerDashboardView.as_view(), name='manager_dashboard'),
    path('employee/', employee_dashboard, name='employee_dashboard'),
    
    # Task template views
    path('tasks/', task_list, name='task_list'),
    path('tasks/create/', task_create, name='create_task'),
    path('tasks/<int:pk>/', task_detail, name='task_detail_page'),
]
