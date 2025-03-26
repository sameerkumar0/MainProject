from django.urls import path
from .views import EmployeeRegisterView, EmployeeProfileView,ManagerRegisterView,manager_login_page,employee_login_page,manager_dashboard,employee_dashboard

urlpatterns = [
    path('employee-register/', EmployeeRegisterView.as_view(), name='user-register'),
    path('profile/', EmployeeProfileView.as_view(), name='employee-profile'),
    path('manager-register/',ManagerRegisterView.as_view(),name="manager-register"),

    path('manager-login/', manager_login_page, name='manager_login'),
    path('employee-login/', employee_login_page, name='employee_login'),
    path("manager-dashboard/", manager_dashboard, name="manager_dashboard"),
    path("employee-dashboard/", employee_dashboard, name="employee_dashboard"),
]
