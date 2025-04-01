from django.urls import path

from .views import ManagerRegisterView,EmployeeRegisterView,LoginView,ForgotPasswordView,ResetPasswordView,reset_password_page,employee_profile,employee_dashboard

urlpatterns = [
    path('register/employee/', EmployeeRegisterView.as_view(), name='register-employee'),
    path('register/manager/', ManagerRegisterView.as_view(), name='register-manager'),
    path('login/', LoginView.as_view(), name='login'),

    # employee
    path("dashboard/", employee_dashboard, name="employee_dashboard"),
    path("profile/", employee_profile, name="employee_profile"),
    
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),
]

