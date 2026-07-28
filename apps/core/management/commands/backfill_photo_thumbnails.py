"""Genera photo_thumb_data (64x64) para usuarios que ya tienen photo_data pero
aun no tienen miniatura (fotos subidas antes de que existiera este campo).

Ejemplos:
  manage.py backfill_photo_thumbnails
  manage.py backfill_photo_thumbnails --dry-run
"""

import io

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from PIL import Image

from apps.accounts.forms import PHOTO_THUMB_SIZE

User = get_user_model()


class Command(BaseCommand):
    help = "Genera la miniatura (photo_thumb_data) a partir de la foto ya guardada en BD."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No guarda cambios, solo cuenta.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = User.objects.exclude(photo_data=None).filter(photo_thumb_data=None)
        count = 0
        for user in qs:
            img = Image.open(io.BytesIO(bytes(user.photo_data))).convert("RGB")
            img = img.resize((PHOTO_THUMB_SIZE, PHOTO_THUMB_SIZE), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            if not dry_run:
                user.photo_thumb_data = buf.getvalue()
                user.save(update_fields=["photo_thumb_data"])
            count += 1

        verb = "Se generarían" if dry_run else "Se generaron"
        self.stdout.write(self.style.SUCCESS(f"{verb} {count} miniatura(s) de foto."))
