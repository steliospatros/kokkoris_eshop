from django.contrib import admin

from administration.models import AdministrationUser


@admin.register(AdministrationUser)
class AdministrationUserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "notes", "added_at")
    list_filter = ("is_active",)
    search_fields = ("email", "notes")
    ordering = ("email",)
