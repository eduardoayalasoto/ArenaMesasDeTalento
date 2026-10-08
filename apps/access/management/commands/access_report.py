"""Reporte previo a la activación (spec 005, FR-011b): qué gana y qué pierde cada persona.

Compara el comportamiento anterior (`apps.access.legacy`) contra el perfil que tendrá cada
persona, y agrega el uso histórico de los accesos que se cierran. Solo lectura.

Uso: manage.py access_report
"""

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.access import registry
from apps.access.legacy import EXPECTED_CHANGES, legacy_for
from apps.access.seed import matrix_for, suggested_profile_slug
from apps.access.registry import Scope


class Command(BaseCommand):
    help = "Lista, por persona, los permisos que se ganan o pierden con la matriz de perfiles."

    def handle(self, *args, **opts):
        from django.db import connection

        User = get_user_model()
        # Funciona antes de migrar (producción aún sin la columna de perfil): usa el perfil sugerido.
        with connection.cursor() as cur:
            cols = {c.name for c in connection.introspection.get_table_description(cur, User._meta.db_table)}
        has_profile = "profile_id" in cols
        fields = ["full_name", "role", "level__code", "is_superuser"] + (["profile__slug"] if has_profile else [])
        users = User.objects.filter(is_active=True, deleted_at__isnull=True, is_superuser=False).select_related(
            "level", *(["profile"] if has_profile else [])).only(*fields).order_by("full_name")
        by_change = defaultdict(list)
        counts = defaultdict(int)
        for u in users:
            slug = suggested_profile_slug(u)
            if has_profile and u.profile_id and u.profile.slug in ("colaborador", "lead", "director", "talento"):
                slug = u.profile.slug
            counts[slug] += 1
            old, new = legacy_for(slug), matrix_for(slug)
            for key in registry.BY_KEY:
                o, n = Scope(old.get(key, 0)), Scope(new.get(key, 0))
                if o != n:
                    by_change[(key, slug, o, n)].append(u.full_name)

        w = self.stdout.write
        w("# Reporte de activación — Matriz de permisos por perfiles\n")
        w("Perfil asignado: " + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + "\n")
        if not by_change:
            w("Nadie gana ni pierde acceso.")
        for (key, slug, o, n), names in sorted(by_change.items()):
            perm = registry.get(key)
            verb = "PIERDE" if n < o else "GANA"
            why = EXPECTED_CHANGES.get((key, slug), "⚠ cambio NO listado como esperado")
            w(f"\n## {verb} · {perm.screen} ({key}) · perfil {slug}: {o.label} → {n.label}")
            w(f"Motivo: {why}")
            w(f"Personas ({len(names)}): " + ", ".join(names))

        # Uso histórico de accesos que se cierran.
        from apps.evaluations.models import ValueDeliveryEvaluation

        w("\n## Uso histórico de accesos que se cierran")
        vd = [v for v in ValueDeliveryEvaluation.objects.select_related("project", "evaluator", "period")
              .only("status", "evaluator__role", "evaluator__full_name", "project__name",
                    "project__responsable_id", "period__name")
              if v.evaluator_id and v.evaluator.role == "DIRECTOR" and v.project.responsable_id != v.evaluator_id]
        if vd:
            for v in vd:
                w(f"- Entrega de Valor capturada por Director no responsable: {v.period} · {v.project.name} · "
                  f"{v.evaluator.full_name} · {v.get_status_display()} (el registro se conserva)")
        else:
            w("- Ninguno.")
