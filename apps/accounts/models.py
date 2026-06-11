"""Modelo de usuario custom: el correo @arena-analytics.com es el identificador."""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager que usa el email como identificador en lugar del username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.TALENTO)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Colaborador de Arena. El rol LEAD no se guarda: deriva de level.code == 'LEAD'."""

    class Role(models.TextChoices):
        COLABORADOR = "COLABORADOR", "Colaborador"
        TALENTO = "TALENTO", "Talento y Cultura"
        DIRECTOR = "DIRECTOR", "Director"

    # Se elimina el username heredado; el email es el identificador.
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("correo electrónico", unique=True)
    full_name = models.CharField("nombre completo", max_length=160)
    area = models.ForeignKey(
        "catalog.Area",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="área",
    )
    level = models.ForeignKey(
        "catalog.SeniorityLevel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="nivel de seniority",
    )
    role = models.CharField(
        "rol",
        max_length=12,
        choices=Role.choices,
        default=Role.COLABORADOR,
    )
    photo = models.ImageField(
        "fotografía", upload_to="fotos/", null=True, blank=True,
        help_text="Obligatoria; se muestra en tus resultados.",
    )
    # La foto se guarda en la BD (Vercel tiene FS de solo lectura): bytes + tipo MIME.
    photo_data = models.BinaryField(null=True, blank=True, editable=False)
    photo_mime = models.CharField(max_length=40, blank=True, default="")
    must_change_password = models.BooleanField(
        "debe cambiar contraseña", default=False,
        help_text="Si está activo, se obliga a crear una nueva contraseña al ingresar.",
    )
    date_joined = models.DateTimeField("fecha de alta", default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name or self.email

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email

    # --- Roles derivados (no se persisten) --------------------------------
    @property
    def is_lead(self) -> bool:
        """Lead de área: deriva del nivel, no del rol (decisión del plan)."""
        return bool(self.level and self.level.code == "LEAD")

    @property
    def is_talento(self) -> bool:
        return self.role == self.Role.TALENTO

    @property
    def is_director(self) -> bool:
        return self.role == self.Role.DIRECTOR

    @property
    def is_admin(self) -> bool:
        """Capacidades de administración: Talento o superusuario."""
        return self.is_superuser or self.is_talento

    @property
    def leads_projects(self) -> bool:
        """Es líder de al menos un proyecto activo."""
        return self.led_projects.filter(is_active=True).exists()

    @property
    def has_photo(self) -> bool:
        return bool(self.photo_data)

    @property
    def initials(self) -> str:
        parts = (self.full_name or self.email).split()
        return (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper()
