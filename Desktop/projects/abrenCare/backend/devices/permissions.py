from rest_framework import permissions
from .models import Device  # Assuming you have a Device model
# OR from your models import Device if Device is in the same app

class IsDeviceOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a device to access or modify it.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        For POST requests, we should allow if the user is authenticated.
        For list views, only show devices belonging to the user.
        """
        # Allow read-only access for safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # For write methods (POST, PUT, PATCH, DELETE), user must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access a specific device object.
        """
        # Allow read-only access for safe methods
        if request.method in permissions.SAFE_METHODS:
            # Check if the device belongs to the user
            return obj.user == request.user
        
        # For write methods, check ownership
        return obj.user == request.user
    