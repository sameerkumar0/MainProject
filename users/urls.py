"""URL configuration for users app API endpoints."""
from django.urls import path
from .views import (
    # Authentication API views
    ManagerRegisterView, EmployeeRegisterView,
    EmployeeLoginView, ManagerLoginView,
    ForgotPasswordView, ResetPasswordView, LogoutView,
    # Employee API views
    EmployeeListView, EmployeeProfileView,
    # Manager API views
    ManagerDashboardAPIView, EmployeeTasksAPIView,
    # Utility API views
    get_csrf_token
)

urlpatterns = [
    # Authentication API endpoints
    path('register/employee/', EmployeeRegisterView.as_view(), name='register_employee_api'),
    path('register/manager/', ManagerRegisterView.as_view(), name='register_manager_api'),
    path('login/employee/', EmployeeLoginView.as_view(), name='employee_login_api'),
    path('login/manager/', ManagerLoginView.as_view(), name='manager_login_api'),
    path('logout/', LogoutView.as_view(), name='logout_api'),

    # Password management API endpoints
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password_api'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password_api'),

    # Employee management API endpoints
    path('employees/', EmployeeListView.as_view(), name='employee_list_api'),
    path('employees/<int:pk>/profile/', EmployeeProfileView.as_view(), name='employee_profile_api'),

    # Manager API endpoints
    path('manager/dashboard/', ManagerDashboardAPIView.as_view(), name='manager_dashboard_api'),
    path('employees/tasks/', EmployeeTasksAPIView.as_view(), name='employee_tasks_api'),

    # Utility API endpoints
    path('csrf/', get_csrf_token, name='csrf_token'),
]
