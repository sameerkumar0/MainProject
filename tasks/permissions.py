from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsManager(permissions.BasePermission):
    """
    Custom permission to allow only Managers to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "Manager"

class IsEmployee(BasePermission):
    """
    Custom permission to grant access only to Employees.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'Employee'


class IsTaskAssignedToEmployee(BasePermission):
    """
    Custom permission to ensure an employee can only update their own assigned tasks.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the user is authenticated and is an employee
        if not (request.user and request.user.is_authenticated and request.user.role == 'Employee'):
            return False

        # Check if the task is assigned to this employee via TaskAssignment
        return obj.assignments.filter(employee=request.user, completed_at__isnull=True).exists()
