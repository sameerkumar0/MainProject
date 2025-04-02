from django.urls import path
from .views import ManagerRegisterView,EmployeeRegisterView,login_view,ForgotPasswordView,ResetPasswordView,reset_password_page,employee_dashboard,register_manager,manager_dashboard

urlpatterns = [
    path('register/employee/', EmployeeRegisterView.as_view(), name='register-employee'),
    path('register/manager/', ManagerRegisterView.as_view(), name='manager-register'),
    path('register/',register_manager,name='manager_register'),
    path('login/', login_view, name='login'),

    # employee
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
    path("manager/dashboard/", manager_dashboard, name="manager_dashboard"),

    
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),
]

