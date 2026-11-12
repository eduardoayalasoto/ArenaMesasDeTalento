"""Catálogos de Puestos y Categorías (spec 008, US4 y US2)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.catalog.forms import PositionForm
from apps.catalog.models import Area, PillarWeight, Position, SeniorityLevel
from apps.core.services import positions
from apps.core.templatetags.core_extras import puesto, puesto_de
from apps.questionnaires.models import Category

User = get_user_model()


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento.puestos@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )


@pytest.fixture
def ladder(db):
    levels = {
        code: SeniorityLevel.objects.create(code=code, name=name, order=i)
        for i, (code, name) in enumerate([("JR", "Junior"), ("MID", "Mid"), ("SNR", "Senior"), ("LEAD", "Lead")], 1)
    }
    for level in levels.values():
        PillarWeight.objects.create(level=level, w_ownership="0.60", w_value_delivery="0.20", w_arena_impact="0.20")
    areas = {"PM": Area.objects.create(code="PM", name="Gestión de Proyectos"),
             "CONS": Area.objects.create(code="CONS", name="Consultoría")}
    return areas, levels


@pytest.mark.django_db
def test_positions_catalog_names_cache_and_validation(ladder, client, talento):
    areas, levels = ladder
    assert positions.ensure_default_positions() == 8
    assert positions.ensure_default_positions() == 0          # idempotente

    cons = User.objects.create_user(email="c1@arena-analytics.com", password=None, full_name="C Uno",
                                    area=areas["CONS"], level=levels["JR"])
    pm = User.objects.create_user(email="p1@arena-analytics.com", password=None, full_name="P Uno",
                                  area=areas["PM"], level=levels["JR"])
    assert [puesto(cons), puesto(pm)] == ["Analista", "Junior"]
    gerente = User(area=areas["CONS"], level=levels["LEAD"])
    assert puesto(gerente) == "Gerente" and puesto(User(area=None, level=None)) == ""

    # Renombrar invalida la caché y no toca la ponderación de pilares del nivel global.
    Position.objects.filter(area=areas["CONS"], level=levels["JR"]).update(name="Analista Jr")
    positions.invalidate()
    assert puesto(cons) == "Analista Jr"
    assert PillarWeight.objects.get(level=levels["JR"]).w_ownership == Decimal("0.60")

    # Sin puesto en el catálogo se muestra el nivel; con puesto inactivo la combinación no está definida.
    Position.objects.filter(area=areas["PM"], level=levels["MID"]).delete()
    assert positions.position_name(areas["PM"].pk, levels["MID"].pk, fallback="Mid") == "Mid"
    Position.objects.filter(area=areas["PM"], level=levels["SNR"]).update(is_active=False)
    positions.invalidate()
    assert not positions.position_defined(areas["PM"], levels["MID"])
    assert not positions.position_defined(areas["PM"], levels["SNR"])
    assert positions.position_defined(areas["PM"], levels["JR"])

    # Objetos con área y nivel (cuestionarios).
    from apps.questionnaires.models import QuestionnaireTemplate

    template = QuestionnaireTemplate(kind="OWNERSHIP", area=areas["CONS"], level=levels["MID"])
    assert puesto_de(template) == "Consultor"

    # Pantalla: Talento renombra un puesto y crea uno que faltaba; las combinaciones no definidas se avisan.
    client.force_login(talento)
    url = reverse("catalog:position_admin")
    assert client.get(url).status_code == 200
    client.post(url, {"area": areas["PM"].pk, "level": levels["MID"].pk, "name": "Mid PM", "is_active": "on"})
    assert Position.objects.get(area=areas["PM"], level=levels["MID"]).name == "Mid PM"
    response = client.post(url, {"area": areas["PM"].pk, "level": levels["MID"].pk, "name": "  "})
    assert "obligatorio" in " ".join(str(m) for m in get_messages(response.wsgi_request))
    assert not PositionForm({"area": 1, "level": 1, "name": "x" * 61}).is_valid()

    # Alta de usuario: combinación sin puesto activo → error claro.
    from apps.accounts.forms import UserCreateForm

    form = UserCreateForm({
        "full_name": "Nuevo", "email": "nuevo@arena-analytics.com", "area": areas["PM"].pk,
        "level": levels["SNR"].pk, "role": "COLABORADOR", "password": "Arena2026!",
    })
    assert not form.is_valid() and "No existe un puesto activo" in str(form.errors["level"])
    form = UserCreateForm({
        "full_name": "Nuevo", "email": "nuevo@arena-analytics.com", "area": areas["PM"].pk,
        "level": levels["JR"].pk, "role": "COLABORADOR", "password": "Arena2026!",
    })
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_category_catalog_screen(client, talento):
    client.force_login(talento)
    url = reverse("catalog:category_admin")
    assert client.get(url).status_code == 200

    client.post(url, {"name": "Delivery al cliente", "order": "1"})
    client.post(url, {"name": "Delivery al cliente", "order": "2"})      # mismo nombre → clave única distinta
    # (las categorías sembradas por la migración ya existen; solo se revisan las que crea la pantalla)
    codes = list(Category.objects.filter(code__startswith="delivery-al-cliente").order_by("pk").values_list("code", flat=True))
    assert codes == ["delivery-al-cliente", "delivery-al-cliente-2"]

    category = Category.objects.get(code="delivery-al-cliente")
    client.post(url, {"category": category.pk, "name": "Delivery", "order": "5"})   # sin is_active → inactiva
    category.refresh_from_db()
    assert (category.name, category.order, category.is_active) == ("Delivery", 5, False)
    before = Category.objects.count()
    response = client.post(url, {"name": "", "order": "1"})
    assert Category.objects.count() == before
    assert "Este campo es obligatorio" in " ".join(str(m) for m in get_messages(response.wsgi_request))
