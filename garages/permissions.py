"""garages/permissions.py — Custom DRF permissions"""
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allows access only to users with role='owner'."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'owner'


class IsCustomer(BasePermission):
    """Allows access only to users with role='customer'."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'


class IsGarageOwner(BasePermission):
    """Object-level: allows access only to the owner of this specific garage."""
    def has_object_permission(self, request, view, obj):
        garage = obj if hasattr(obj, 'owner') else getattr(obj, 'garage', None)
        if garage is None:
            return False
        return garage.owner == request.user
