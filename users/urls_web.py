"""
URL configuration for users app web views.
"""
from django.urls import path
from django.shortcuts import render
from .views import (
    register_manager, register_emp,
    emp_login_page, manager_login_page,
    list_employee, logout_view,
    reset_password_page, forgot_password_page, employee_profile,
    manager_employee_dashboard, employee_tasks_view,
    manager_login_test
)

urlpatterns = [
    # Authentication pages
    path('register/manager/', register_manager, name='manager_register'),
    path('register/employee/', register_emp, name='register_employee'),
    path('login/manager/', manager_login_page, name='manager_login'),
    path('login/manager/test/', manager_login_test, name='manager_login_test'),
    path('login/employee/', emp_login_page, name='employee_login'),
    path('logout/', logout_view, name='logout_page'),
    path('reset-password/', reset_password_page, name='reset_password_page'),
    path('forgot-password/', forgot_password_page, name='forgot_password_page'),

    # Employee management pages
    path('employees/', list_employee, name='list_employees'),
    path('employees/<int:pk>/profile/', employee_profile, name='employee_profile'),

    # Manager dashboard pages
    path('manager/employees/', manager_employee_dashboard, name='manager_employee_dashboard'),
    path('manager/employee-tasks/', employee_tasks_view, name='employee_tasks_view'),

]
