import frappe
from frappe.model.document import Document


class MatchaSettings(Document):
    """
    Container for global Matcha configuration.

    This doctype is intentionally small and focused on feature flags and
    sensible defaults so it can evolve without impacting core flows.
    """

    def validate(self):
        if not self.is_new() and not self.has_value_changed("invoice_field_config"):
            return
        from matcha.api.invoice_fields import validate_configuration

        validate_configuration(self.get("invoice_field_config"))

    @staticmethod
    def get_settings():
        """Return the singleton Matcha Settings document."""
        return frappe.get_single("Matcha Settings")

