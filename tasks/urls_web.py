"""
URL configuration for tasks app web views.
"""
from django.urls import path
from .views import (
    task_create, task_list, task_detail, task_assign
)
from django.views.generic import TemplateView
from users.views import employee_dashboard

urlpatterns = [
    # Default view (redirects to task list)
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Task template views
    path('tasks/', task_list, name='task_list'),
    path('tasks/create/', task_create, name='create_task'),
    path('tasks/<int:pk>/', task_detail, name='task_detail_page'),
    path('tasks/<int:pk>/progress/', TemplateView.as_view(template_name='tasks/task_progress.html'), name='task_progress'),
    path('tasks/assign/', task_assign, name='task-assign'),

    # Dashboard views
    path('employee_dashboard/', employee_dashboard, name='employee_dashboard'),

    # Notification and Activity views
    path('notifications/', TemplateView.as_view(template_name='tasks/notification_list.html'), name='notification_list'),
    path('activities/', TemplateView.as_view(template_name='tasks/user_activity.html'), name='user_activity'),
]
