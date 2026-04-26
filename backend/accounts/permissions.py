from rest_framework.permissions import BasePermission


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", None)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) == "admin"


class IsClientUser(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) in {"admin", "client"}


class IsOwnerClientOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if user_role(request.user) == "admin":
            return True

        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "business_client"):
            owner = getattr(obj.business_client, "owner", None)

        return owner == request.user

