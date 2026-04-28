from rest_framework.permissions import BasePermission


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", None)


def profile_business_client(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "business_client", None)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) == "admin"


class IsClientUser(BasePermission):
    def has_permission(self, request, view):
        return user_role(request.user) in {"admin", "client", "employee"}


class IsOwnerClientOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if user_role(request.user) == "admin":
            return True

        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "business_client"):
            owner = getattr(obj.business_client, "owner", None)

        if owner == request.user:
            return True

        employee_client = profile_business_client(request.user)
        object_client = getattr(obj, "business_client", None)
        if employee_client and object_client:
            return object_client.id == employee_client.id

        return False
