"""
Properties services — Business logic for property management.
"""

from properties.models import PricingPlan, Property


class PropertyService:
    """Property management business logic."""

    @staticmethod
    def publish(property_obj):
        """Publish a property, making it visible."""
        if not hasattr(property_obj, "location") or not property_obj.location:
            raise ValueError("Property must have a location before publishing.")
        if property_obj.pricing_plans.filter(is_active=True).count() == 0:
            raise ValueError("Property must have at least one active pricing plan.")
        property_obj.status = Property.Status.PUBLISHED
        property_obj.save(update_fields=["status", "updated_at"])
        return property_obj

    @staticmethod
    def unpublish(property_obj):
        """Unpublish a property."""
        property_obj.status = Property.Status.DRAFT
        property_obj.save(update_fields=["status", "updated_at"])
        return property_obj


class PricingPlanService:
    """Pricing plan business logic."""

    @staticmethod
    def activate(plan):
        """Activate a pricing plan."""
        plan.is_active = True
        plan.save(update_fields=["is_active", "updated_at"])
        return plan

    @staticmethod
    def deactivate(plan):
        """Deactivate a pricing plan."""
        plan.is_active = False
        plan.save(update_fields=["is_active", "updated_at"])
        return plan

    @staticmethod
    def lock_plan(plan):
        """Lock a plan's spread method after it's used in a subscription."""
        if not plan.is_locked:
            plan.is_locked = True
            plan.save(update_fields=["is_locked", "updated_at"])
