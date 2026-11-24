"""Formularios de cuenta, con etiquetas y mensajes en español."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django import forms
from django.db.models import Q

from apps.core.forms import INPUT_CLASSES, SELECT_CLASSES  # clases daisyUI canónicas (igual que arena-crm)

User = get_user_model()


PHOTO_SIZE = 400
PHOTO_THUMB_SIZE = 64


def square_jpeg_bytes(upload, size: int = PHOTO_SIZE) -> bytes:
    """Recorta a cuadrado y devuelve la imagen como JPEG `size`x`size` (bytes), en memoria."""
    import io

    from PIL import Image, ImageOps

    upload.seek(0)
    img = Image.open(upload)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


_INPUT = INPUT_CLASSES
_SELECT = SELECT_CLASSES


class EmailAuthenticationForm(AuthenticationForm):
    """Login por correo electrónico (el USERNAME_FIELD es el email)."""

    username = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "nombre@arena-analytics.com",
                "class": INPUT_CLASSES,
            }
        ),
    )

    error_messages = {
        # Genérico (no revela si el correo existe), en una línea -- igual que arena-crm.
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Tu cuenta está desactivada. Contacta a Talento y Cultura.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update(
            {"class": INPUT_CLASSES, "autocomplete": "current-password",
             "placeholder": "Tu contraseña"}
        )


class PhotoForm(forms.ModelForm):
    """Subida de fotografía (obligatoria). Se recorta a un cuadrado y se redimensiona."""

    class Meta:
        model = User
        fields = ["photo"]
        labels = {"photo": "Fotografía"}

    photo = forms.ImageField(
        label="Fotografía",
        error_messages={
            "required": "Sube una fotografía; es obligatoria.",
            "invalid_image": "El archivo no es una imagen válida. Usa JPG o PNG.",
        },
        widget=forms.ClearableFileInput(attrs={"class": "file-input w-full", "accept": "image/*"}),
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        upload = self.cleaned_data.get("photo")
        if upload and hasattr(upload, "file"):
            user.photo_data = square_jpeg_bytes(upload)
            user.photo_thumb_data = square_jpeg_bytes(upload, size=PHOTO_THUMB_SIZE)
            user.photo_mime = "image/jpeg"
        if commit:
            user.save()
        return user


class ProfileInfoForm(forms.ModelForm):
    """Información personal: nombre (editable) y foto (se recorta a cuadrado)."""

    class Meta:
        model = User
        fields = ["full_name"]  # 'photo' es solo del formulario (no toca el ImageField del modelo)
        labels = {"full_name": "Nombre para mostrar"}
        widgets = {
            "full_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Como quieres que aparezca tu nombre"}),
        }

    photo = forms.ImageField(
        required=False,
        error_messages={"invalid_image": "El archivo no es una imagen válida. Usa JPG o PNG."},
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "class": "sr-only"}),
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        upload = self.cleaned_data.get("photo")
        fields = ["full_name"]
        if upload and hasattr(upload, "file"):
            user.photo_data = square_jpeg_bytes(upload)
            user.photo_thumb_data = square_jpeg_bytes(upload, size=PHOTO_THUMB_SIZE)
            user.photo_mime = "image/jpeg"
            fields += ["photo_data", "photo_thumb_data", "photo_mime"]
        if commit:
            user.save(update_fields=fields)
        return user


class UserAdminForm(forms.ModelForm):
    """Alta y edición de una persona por Talento, con todas sus propiedades.

    Sin `instance` es alta (pide contraseña inicial); con `instance` es edición. El perfil no es
    campo del modelo aquí: lo asigna el servicio para que quede en la bitácora de permisos.
    """

    password = forms.CharField(
        label="Contraseña inicial",
        initial="Arena2026!",
        widget=forms.TextInput(attrs={"class": _INPUT}),
        help_text="La persona entrará con esta contraseña.",
    )
    must_change_password = forms.BooleanField(
        label="Pedir cambio de contraseña al ingresar", required=False, initial=True,
    )
    profile = forms.ModelChoiceField(
        label="Perfil de permisos", queryset=None, required=False,
        empty_label="— Sugerido por rol y nivel —",
        widget=forms.Select(attrs={"class": _SELECT}),
        help_text="Define qué puede ver y hacer en el sistema.",
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "area", "level", "role", "direct_lead", "is_lead_flag", "is_director_flag",
                  "is_active"]
        labels = {
            "full_name": "Nombre completo",
            "email": "Correo electrónico",
            "area": "Posición",
            "level": "Nivel (opcional)",
            "role": "Rol",
            "direct_lead": "Lead directo",
            "is_lead_flag": "Lead / Gerente",
            "is_director_flag": "Director",
            "is_active": "Cuenta activa (puede ingresar)",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Nombre y apellidos"}),
            "email": forms.EmailInput(attrs={"class": _INPUT, "placeholder": "nombre@arena-analytics.com"}),
            "area": forms.Select(attrs={"class": _SELECT}),
            "level": forms.Select(attrs={"class": _SELECT}),
            "role": forms.Select(attrs={"class": _SELECT}),
            "direct_lead": forms.Select(attrs={"class": _SELECT}),
            "is_lead_flag": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_director_flag": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, actor=None, can_assign_profiles=False, **kwargs):
        from apps.access import services as access
        from apps.access.models import Profile

        super().__init__(*args, **kwargs)
        self.actor = actor
        self.creating = self.instance.pk is None
        self.fields["area"].required = False
        self.fields["level"].required = False
        self.fields["area"].empty_label = "— Sin posición —"
        self.fields["level"].empty_label = "— Sin nivel —"
        self.fields["level"].help_text = "Solo si la posición lo usa (p. ej. Consultor Senior o los niveles de Analítica)."
        self.fields["is_lead_flag"].help_text = "Lidera a un equipo: evalúa como líder y puede ser Lead directo."
        self.fields["is_director_flag"].help_text = "Está en la cima del organigrama de su área."
        self.fields["direct_lead"].required = False
        self.fields["direct_lead"].empty_label = "— Lead del área —"
        eligible = access.assignable_users("assign.direct_lead").values("pk")
        # Se conserva el Lead actual aunque ya no sea elegible, para no bloquear la edición de otros datos.
        self.fields["direct_lead"].queryset = User.objects.filter(
            Q(pk__in=eligible) | Q(pk=self.instance.direct_lead_id)).exclude(pk=self.instance.pk).order_by("full_name")
        self.fields["direct_lead"].help_text = "Primer aprobador de sus solicitudes de curso en Arena Learn."
        self.fields["role"].help_text = "Talento administra; Director valida Entrega de Valor."
        if can_assign_profiles:
            self.fields["profile"].queryset = Profile.objects.filter(is_system=False).order_by("name")
            if not self.creating:
                self.fields["profile"].initial = self.instance.profile_id
                if self.instance.profile_id:
                    self.fields["profile"].empty_label = None
        else:
            del self.fields["profile"]
        if self.creating:
            self.fields["is_active"].initial = True
        else:
            del self.fields["password"]
            del self.fields["must_change_password"]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_is_active(self):
        active = self.cleaned_data["is_active"]
        if not active and self.actor is not None and self.instance.pk == self.actor.pk:
            raise forms.ValidationError("No puedes desactivar tu propia cuenta.")
        return active

    def clean(self):
        cleaned = super().clean()
        area, level = cleaned.get("area"), cleaned.get("level")
        unchanged = (not self.creating and area == self.instance.area and level == self.instance.level)
        if area and level and not unchanged:
            from apps.core.services import positions

            if not positions.position_defined(area, level):
                self.add_error("level", f"No existe una posición activa para {area.name} · {level.name} (Catálogos → Posiciones).")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.creating:
            user.set_password(self.cleaned_data["password"])
            user.must_change_password = self.cleaned_data.get("must_change_password", False)
        if commit:
            user.save()
        return user


class SpanishPasswordChangeForm(PasswordChangeForm):
    """Cambio de contraseña con etiquetas en español."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "old_password": "Contraseña actual",
            "new_password1": "Nueva contraseña",
            "new_password2": "Confirma la nueva contraseña",
        }
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)
            field.widget.attrs.update({"class": INPUT_CLASSES, "autocomplete": "new-password"})


class SpanishSetPasswordForm(SetPasswordForm):
    """Nueva contraseña desde el enlace de restablecimiento, con widgets daisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nueva contraseña"
        self.fields["new_password2"].label = "Confirma la contraseña"
        for field in self.fields.values():
            field.widget.attrs.update({"class": INPUT_CLASSES, "autocomplete": "new-password"})
