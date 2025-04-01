from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsManager(permissions.BasePermission):
    """
    Custom permission to allow only managers to create employees.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "manager"


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'employee'
