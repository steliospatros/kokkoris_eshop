from django.db import models


class AdministrationUser(models.Model):
    """
    Allow-list of emails that can access the shop administration panel.
    Managed manually via Django admin — not tied to is_staff / is_superuser.
    """

    ROLE_ADMIN = "admin"
    ROLE_COURIER = "courier"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Διαχειριστής"),
        (ROLE_COURIER, "Courier"),
    )

    email = models.EmailField(
        unique=True,
        help_text="Login email of a user who may open the administration panel.",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ADMIN,
        help_text="Admins see the full panel. Couriers only see Παραδόσεις.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to revoke access without deleting the record.",
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional note for internal use (e.g. role or name).",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Administration user"
        verbose_name_plural = "Administration users"
        ordering = ["email"]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"{self.email} ({self.get_role_display()}, {status})"

    @property
    def is_shop_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_courier(self):
        return self.role == self.ROLE_COURIER
