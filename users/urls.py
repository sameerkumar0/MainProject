from django.urls import path
from .views import (ManagerRegisterView,EmployeeRegisterView,login_view,ForgotPasswordView,ResetPasswordView,
                    get_csrf_token,reset_password_page,employee_dashboard,register_manager,ManagerDashboardView
                    ,dashboard_Page)

urlpatterns = [
    path('register/employee/', EmployeeRegisterView.as_view(), name='register-employee'),
    path('register/manager/', ManagerRegisterView.as_view(), name='manager-register'),
    path('register/',register_manager,name='manager_register'),
    path('login/', login_view, name='login'),

    # employee
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
        path("manager/dashboard/", ManagerDashboardView.as_view(), name="manager-dashboard"),
        path('dashboard/',dashboard_Page,name='manager_dasboard'),

    
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),

    path("csrf/", get_csrf_token, name="csrf_token"),
]

