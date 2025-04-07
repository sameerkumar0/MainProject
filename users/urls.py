from django.urls import path
from django.shortcuts import render
from .views import (ManagerRegisterView, EmployeeRegisterView, EmployeeLoginView, ManagerLoginView, ForgotPasswordView, ResetPasswordView,
                    get_csrf_token, reset_password_page, employee_dashboard, register_manager, ManagerDashboardView, EmployeeDashboardView,
                    dashboard_Page, register_emp, emp_login_page, manager_login_page,
                    EmployeeListView, list_employee, LogoutView, logout_view)

urlpatterns = [

    #Register urls
    path('register/employee/', EmployeeRegisterView.as_view(), name="register_employee"),
    path('register/manager/', ManagerRegisterView.as_view(), name='manager-register'),
    path('register/',register_manager,name='manager_register'),
    path('emp_register/',register_emp,name='register-employee'),


    #login urls
    path("login/employee/", EmployeeLoginView.as_view(), name="employee_login"),
    path("login/manager/", ManagerLoginView.as_view(), name="manager_login"),
    path('emp_login/',emp_login_page,name='emp_login'),
    path('manager_login/',manager_login_page,name='manager-login'),



    # Dashboard Urls
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
    path("manager/dashboard/", ManagerDashboardView.as_view(), name="manager-dashboard"),
    path('dashboard/',dashboard_Page,name='manager_dasboard'),
    path('emp_dashboard/',employee_dashboard,name='employee_dashboard'),
    path('employee/tasks/', EmployeeDashboardView.as_view(), name='employee-tasks-api'),

    # forgot password urls
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-page/', reset_password_page, name='reset-password-page'),



    #employee list
    path('list_employee/',EmployeeListView.as_view(),name='emaployee_list'),
    path('employees/',list_employee,name='list_employees'),
    path('employee-tasks/', lambda request: render(request, 'employee_tasks.html'), name='employee-tasks'),

    # Logout URLs
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout-page/', logout_view, name='logout-page'),

    path("csrf/", get_csrf_token, name="csrf_token"),
]

