from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners/admins of an object to edit or delete it.
    Read-only operations (GET, HEAD, OPTIONS) are allowed for any request.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = (
            getattr(obj, "user", None) or getattr(obj, "admin", None) or getattr(obj, "owner", None)
        )
        return owner == request.user
