from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "ra", "role", "course", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "name", "ra")
    fields = ("email", "name", "ra", "role", "course", "is_active", "is_staff", "is_superuser", "last_login", "date_joined")
    readonly_fields = ("last_login", "date_joined")
