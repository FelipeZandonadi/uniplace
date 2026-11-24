from django.contrib import admin

from .models import Vaga


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "curso", "prazo", "aberta", "autor")
    list_filter = ("tipo", "aberta")
