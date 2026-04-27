from audit_log.models import AuditLog


def write_audit_log(
    action,
    business_client=None,
    actor=None,
    object_type="",
    object_id="",
    channel="system",
    ip_address=None,
    metadata=None,
):
    return AuditLog.objects.create(
        business_client=business_client,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        channel=channel,
        ip_address=ip_address,
        metadata=metadata or {},
    )
