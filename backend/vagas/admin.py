from django.contrib import admin

from .models import Candidatura, Vaga


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "curso", "prazo", "aberta", "autor")
    list_filter = ("tipo", "aberta")


@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ("vaga", "aluno", "status", "created_at")
    list_filter = ("status",)
