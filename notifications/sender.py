"""
Centralised sender-address resolution for all outbound emails.

Auth / onboarding (workspace=None):
    Terratrail Team <no-reply@mail.terratrail.app>

Workspace-triggered (workspace provided):
    {Workspace Name} <{workspace_slug}@mail.terratrail.app>
"""
from django.conf import settings

MAIL_DOMAIN = getattr(settings, "MAIL_DOMAIN", "mail.terratrail.app")
AUTH_FROM    = f"Terratrail Team <no-reply@{MAIL_DOMAIN}>"


def resolve_sender(workspace=None) -> str:
    """Return the correct From address for an email."""
    if workspace is None:
        return AUTH_FROM
    slug = (workspace.slug or "noreply").lower().replace(" ", "-")
    name = workspace.name or "Terratrail"
    return f"{name} <{slug}@{MAIL_DOMAIN}>"
