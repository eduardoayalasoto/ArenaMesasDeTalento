"""Switch para forzar el cambio de contraseña (p. ej. en la primera salida a producción).

Ejemplos:
  manage.py require_password_change --all
  manage.py require_password_change --email ana@arena-analytics.com
  manage.py require_password_change --all --temp-password "Arena-Temp-2026"   (fija contraseña temporal)
  manage.py require_password_change --all --clear                              (desactiva el switch)
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Activa (o limpia) la obligación de cambiar contraseña al ingresar."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Aplica a todos los usuarios activos no superusuarios.")
        parser.add_argument("--email", action="append", default=[], help="Correo específico (repetible).")
        parser.add_argument("--temp-password", help="Fija esta contraseña temporal a los usuarios afectados.")
        parser.add_argument("--clear", action="store_true", help="Desactiva el switch en lugar de activarlo.")

    def handle(self, *args, **options):
        if not options["all"] and not options["email"]:
            raise CommandError("Indica --all o al menos un --email.")

        qs = User.objects.all()
        if options["all"]:
            qs = qs.filter(is_active=True, is_superuser=False)
        else:
            qs = qs.filter(email__in=[e.lower() for e in options["email"]])

        value = not options["clear"]
        temp = options.get("temp_password")
        count = 0
        for user in qs:
            user.must_change_password = value
            if value and temp:
                user.set_password(temp)
            user.save()
            count += 1

        action = "activó" if value else "limpió"
        extra = " (con contraseña temporal)" if (value and temp) else ""
        self.stdout.write(self.style.SUCCESS(
            f"Se {action} el cambio de contraseña obligatorio en {count} usuario(s){extra}."
        ))
