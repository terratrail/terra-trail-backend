"""
Core models — Workspace and abstract base models.

Every tenant-scoped model in the system inherits from WorkspaceScopedModel,
ensuring consistent multi-tenancy enforcement at the model layer.
"""

import uuid
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Abstract base with automatic created/updated timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Workspace(TimeStampedModel):
    """
    Represents a real estate company / tenant.

    All data in the system is scoped to a workspace.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    logo = models.ImageField(upload_to="workspaces/logos/", blank=True, null=True)
    timezone = models.CharField(max_length=63, default="UTC")
    support_email = models.EmailField(blank=True, default="")
    support_whatsapp = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Workspace.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class WorkspaceScopedModel(TimeStampedModel):
    """
    Abstract base for all workspace-scoped models.

    Enforces the multi-tenancy FK on every child model.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True


class WorkspaceScopedManager(models.Manager):
    """Manager that filters querysets by workspace."""

    def for_workspace(self, workspace):
        return self.get_queryset().filter(workspace=workspace)
