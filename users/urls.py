from django.urls import path
from .views import (ManagerRegisterView,EmployeeRegisterView,EmployeeLoginView,ManagerLoginView,ForgotPasswordView,ResetPasswordView,
                    get_csrf_token,reset_password_page,employee_dashboard,register_manager,ManagerDashboardView
                    ,dashboard_Page,register_emp,emp_login_page,)

urlpatterns = [
    path('register/employee/', EmployeeRegisterView.as_view(), name="register_employee"),
    path('register/manager/', ManagerRegisterView.as_view(), name='manager-register'),
    path('register/',register_manager,name='manager_register'),
    path('emp_register/',register_emp,name='register-employee'),
    path("login/employee/", EmployeeLoginView.as_view(), name="employee_login"),
    path("login/manager/", ManagerLoginView.as_view(), name="manager_login"),
    path('emp_login/',emp_login_page,name='login-page'),

    

    # employee
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
    path("manager/dashboard/", ManagerDashboardView.as_view(), name="manager-dashboard"),
    path('dashboard/',dashboard_Page,name='manager_dasboard'),

    
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),

    path("csrf/", get_csrf_token, name="csrf_token"),
]

