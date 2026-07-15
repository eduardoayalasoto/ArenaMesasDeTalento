"""TalentSessionNote debe tener un campo `comentarios` de Mesa de Talento, separado
de `comentarios_adicionales` (que pertenece a la sesión de retroalimentación)."""

import pytest

from apps.evaluations.models import TalentSessionNote


@pytest.mark.django_db
def test_comentarios_default_vacio(collaborator, period):
    note = TalentSessionNote.objects.create(user=collaborator, period=period)
    assert note.comentarios == ""


@pytest.mark.django_db
def test_comentarios_se_guarda_y_no_se_confunde_con_comentarios_adicionales(collaborator, period):
    note = TalentSessionNote.objects.create(
        user=collaborator, period=period,
        comentarios="Comentario general de la sesión de Mesa.",
        comentarios_adicionales="Comentario de la sesión de retroalimentación.",
    )
    note.refresh_from_db()
    assert note.comentarios == "Comentario general de la sesión de Mesa."
    assert note.comentarios_adicionales == "Comentario de la sesión de retroalimentación."
