from rest_framework.permissions import BasePermission

class IsManager(BasePermission):
    """
    Custom permission to grant access only to Managers.
    """
    def has_permission(self, request, view):
         return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', None) == 'manager')


class IsEmployee(BasePermission):
    """
    Custom permission to grant access only to Employees.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'employee'


class IsTaskAssignedToEmployee(BasePermission):
    """
    Custom permission to ensure an employee can only update their own assigned tasks.
    """
    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated and obj.assigned_to == request.user
