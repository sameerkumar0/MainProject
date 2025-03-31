from django.urls import path

from .views import RegisterView,LoginView,ForgotPasswordView,ResetPasswordView,reset_password_page,employee_profile,employee_dashboard

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # employee
    path("dashboard/", employee_dashboard, name="employee_dashboard"),
    path("profile/", employee_profile, name="employee_profile"),
    path("api/login/", LoginView.as_view(), name="api_login"),


    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),
]

