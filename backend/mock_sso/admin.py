from django.contrib import admin

from .models import MockIdentity


@admin.register(MockIdentity)
class MockIdentityAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "ra", "role", "course")
    exclude = ("password",)
