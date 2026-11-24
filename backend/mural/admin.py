from django.contrib import admin

from .models import Aviso


@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "prioridade", "autor", "created_at")
    list_filter = ("categoria", "prioridade")
