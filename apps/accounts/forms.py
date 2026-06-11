"""Formularios de cuenta, con etiquetas y mensajes en español."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django import forms

User = get_user_model()

_INPUT = (
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 "
    "shadow-sm focus:border-arena-600 focus:ring-2 focus:ring-arena-200 "
    "focus:outline-none transition"
)


class EmailAuthenticationForm(AuthenticationForm):
    """Login por correo electrónico (el USERNAME_FIELD es el email)."""

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "placeholder": "nombre@arena-analytics.com",
                "class": _INPUT,
            }
        ),
    )

    error_messages = {
        "invalid_login": "El correo o la contraseña no son correctos. "
        "Verifica e intenta de nuevo.",
        "inactive": "Tu cuenta está desactivada. Contacta a Talento y Cultura.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update(
            {"class": _INPUT, "autocomplete": "current-password",
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
        widget=forms.ClearableFileInput(attrs={"class": _INPUT, "accept": "image/*"}),
    )

    def save(self, commit=True):
        import io

        from django.core.files.base import ContentFile
        from PIL import Image, ImageOps

        user = super().save(commit=False)
        upload = self.cleaned_data.get("photo")
        if upload and hasattr(upload, "file"):
            img = Image.open(upload)
            img = ImageOps.exif_transpose(img).convert("RGB")
            # Recorte centrado a cuadrado y escala a 400x400 (sin deformar).
            img = ImageOps.fit(img, (400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            user.photo.save(f"u{user.pk}.jpg", ContentFile(buf.getvalue()), save=False)
        if commit:
            user.save()
        return user


class ProfileInfoForm(forms.ModelForm):
    """Información personal: nombre (editable) y foto (se recorta a cuadrado)."""

    class Meta:
        model = User
        fields = ["full_name", "photo"]
        labels = {"full_name": "Nombre para mostrar", "photo": "Fotografía"}
        widgets = {
            "full_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Como quieres que aparezca tu nombre"}),
        }

    photo = forms.ImageField(
        required=False,
        error_messages={"invalid_image": "El archivo no es una imagen válida. Usa JPG o PNG."},
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "class": "sr-only"}),
    )

    def save(self, commit=True):
        import io

        from django.core.files.base import ContentFile
        from PIL import Image, ImageOps

        user = super().save(commit=False)
        upload = self.cleaned_data.get("photo")
        if upload and hasattr(upload, "file"):
            img = Image.open(upload)
            img = ImageOps.exif_transpose(img).convert("RGB")
            img = ImageOps.fit(img, (400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            user.photo.save(f"u{user.pk}.jpg", ContentFile(buf.getvalue()), save=False)
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
            field.widget.attrs.update({"class": _INPUT, "autocomplete": "new-password"})
