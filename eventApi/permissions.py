from rest_framework import permissions

class IsOrganizerOrAdmin(permissions.BasePermission):
    """
    Allows access only to users with role = admin or organizer
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ["admin", "organizer"]
        )
