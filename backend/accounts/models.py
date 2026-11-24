from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)  # password=None -> senha inutilizável
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=User.Role.ADMIN)
        return self.create_user(email, password, **extra)

    def sync_from_sso(self, identity):
        """Cria/atualiza o usuário a partir das claims do IdP (fonte da verdade do vínculo)."""
        fields = {"name": identity.name, "ra": identity.ra, "role": identity.role, "course": identity.course}
        user, _ = self.update_or_create(
            email=identity.email.lower(),
            defaults=fields,
            # A UniPlace não guarda senhas: usuários vindos do SSO nunca têm senha local.
            create_defaults={**fields, "password": make_password(None)},
        )
        return user


class User(AbstractUser):
    class Role(models.TextChoices):
        ALUNO = "aluno", "Aluno"
        PROFESSOR = "professor", "Professor"
        COLABORADOR = "colaborador", "Colaborador"
        ADMIN = "admin", "Administrador"

    username = None
    first_name = None
    last_name = None
    email = models.EmailField("e-mail", unique=True)
    name = models.CharField("nome", max_length=150)
    ra = models.CharField("RA", max_length=20, blank=True)
    role = models.CharField("papel", max_length=20, choices=Role.choices, default=Role.ALUNO)
    course = models.CharField("curso", max_length=120, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.name} <{self.email}>"
