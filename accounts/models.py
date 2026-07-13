from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser, required because the model drops the
    'username' field entirely and uses 'email' as the unique identifier
    for authentication instead.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user (customer) with the given email/password."""
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save an admin (superuser) account."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for the shop's customers and staff.

    Authentication is done via email + password (or via Google/Facebook
    social login through django-allauth) instead of a Django 'username'.

    The delivery-related fields below are intentionally optional: they are
    NOT collected at registration time. They stay empty until the customer
    fills them in during their first checkout (Part 4), at which point they
    are saved permanently to their account for future orders.
    """
    email = models.EmailField(unique=True, help_text="Used as the login identifier.")
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # --- Delivery details: optional at signup, filled in during checkout. ---
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Greek mobile (69XXXXXXXX). Required at signup; optional until then on legacy accounts.",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City of residence. Filled in during checkout, not at signup."
    )
    area = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Neighborhood / suburb (e.g. Χαλανδρί when city is Αθήνα).",
    )
    street = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Street name (route) from parsed delivery address.",
    )
    street_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Street number from parsed delivery address.",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legacy single-line address (street + number). Kept for checkout compat.",
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="Postal code (T.K.). Filled in during checkout, not at signup."
    )
    delivery_notes = models.TextField(
        blank=True,
        help_text="Special delivery instructions. Filled in during checkout, not at signup."
    )
    floor = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Delivery floor (preset or custom). Filled in during checkout.",
    )
    doorbell_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Name on the doorbell / intercom at delivery address.",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS latitude of the delivery address pin, set via Google Maps at checkout."
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS longitude of the delivery address pin, set via Google Maps at checkout."
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the mobile number was confirmed via SMS OTP.",
    )

    # --- Django auth/admin bookkeeping fields. ---
    is_staff = models.BooleanField(
        default=False,
        help_text="Whether the user can access the Django admin site."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Unselect this instead of deleting accounts."
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # 'email' and 'password' are already required by default.

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        return self.first_name or self.email
