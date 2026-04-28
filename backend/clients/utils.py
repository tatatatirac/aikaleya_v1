from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user


def client_for_request(request):
    if not request.user or not request.user.is_authenticated:
        return None

    role = user_role(request.user)
    if role == "admin":
        client_id = request.query_params.get("client_id") or request.data.get("business_client")
        if client_id:
            return BusinessClient.objects.get(id=client_id)
        return BusinessClient.objects.first()

    if role == "employee":
        profile = getattr(request.user, "profile", None)
        return getattr(profile, "business_client", None)

    return get_active_client_for_user(request.user)
