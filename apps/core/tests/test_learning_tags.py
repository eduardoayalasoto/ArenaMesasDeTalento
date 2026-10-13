"""Arena Learn 006 · US1: etiquetas gestionables (servicio, filtro y vistas). Compactas por escenario."""

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.core.services import learning_flow as flow
from apps.core.services import learning_tags as tags
from apps.core.tests.conftest import learn_request_data
from apps.learning.models import CatalogCourse, Tag


def course(name, *tag_names):
    c = CatalogCourse.objects.create(name=name, provider="MS Learn", url=f"https://learn.microsoft.com/{name}")
    c.tags.set(tags.resolve(tag_names))
    return c


@pytest.mark.django_db
def test_resolve_suggest_filter_and_inactive(learn_people):
    p = learn_people
    # Escenario 2 + borde: " KO ", "ko" y "Kó" son la misma etiqueta; la que no existe se crea.
    ko = tags.resolve(["KO"])[0]
    assert tags.resolve([" ko ", "Kó", "dbt"]) == [ko, Tag.objects.get(key="dbt")]
    assert Tag.objects.count() == 2
    assert tags.clean_names(["Power  BI", "power bi", ""]) == ["Power BI"]
    with pytest.raises(ValidationError):
        tags.clean_names([f"t{i}" for i in range(tags.MAX_TAGS + 1)])

    # Escenario 1: sugerencia por subcadena, sin acentos ni mayúsculas.
    pbi = tags.resolve(["Power BI"])[0]
    assert list(tags.suggest("po")) == [pbi]
    assert list(tags.suggest("po", exclude=["power bi"])) == []

    # Escenario 3: filtro AND en el catálogo.
    a = course("a", "KO", "Power BI")
    course("b", "KO")
    course("c", "Fabric")
    assert {c.name for c in flow.catalog_queryset({"tags": [ko.pk]})} == {"a", "b"}
    fabric = Tag.objects.get(key="fabric")
    assert list(flow.catalog_queryset({"tags": [ko.pk, fabric.pk]})) == []
    assert list(flow.catalog_queryset({"tags": [ko.pk, pbi.pk]})) == [a]
    assert {c.name for c in flow.catalog_queryset({"q": "power"})} == {"a"}  # búsqueda por etiqueta

    # Escenario 5: desactivada = no se sugiere ni se asigna de nuevo, pero sigue en quien la tenía.
    with pytest.raises(PermissionDenied):
        tags.set_active(ko, False, p["colab"])
    tags.set_active(ko, False, p["talento"])
    assert ko not in tags.suggest("ko")
    with pytest.raises(ValidationError, match="desactivada"):
        tags.resolve(["KO"])
    tags.set_tags(a, ["KO", "Power BI"], p["talento"])  # ya la tenía: se conserva
    assert set(a.tags.values_list("name", flat=True)) == {"KO", "Power BI"}


@pytest.mark.django_db
def test_rename_and_merge(learn_people):
    p = learn_people
    c1, c2, c3 = course("x1", "PowerBI"), course("x2", "PowerBI", "Power BI"), course("x3", "Power BI")
    src, dst = Tag.objects.get(key="powerbi"), Tag.objects.get(key="power bi")
    req = flow.create_request(p["colab"], learn_request_data(tags=["PowerBI"]))

    with pytest.raises(ValidationError, match="fusiónalas"):
        tags.rename(src, "power bi", p["talento"])
    with pytest.raises(ValidationError):
        tags.merge(dst, dst, p["talento"])
    with pytest.raises(PermissionDenied):
        tags.merge(src, dst, p["colab"])

    # Escenario 4: fusionar sin duplicados; la de origen desaparece.
    tags.merge(src, dst, p["talento"])
    assert not Tag.objects.filter(pk=src.pk).exists()
    assert set(dst.courses.all()) == {c1, c2, c3} and list(dst.requests.all()) == [req]

    tags.set_active(dst, False, p["talento"])
    other = tags.resolve(["Fabric"])[0]
    with pytest.raises(ValidationError, match="desactivada"):
        tags.merge(other, dst, p["talento"])
    assert tags.rename(other, "Microsoft Fabric", p["talento"]).key == "microsoft fabric"


@pytest.mark.django_db
def test_tag_views_and_forms(client, learn_people, catalog_course):
    p = learn_people
    # El colaborador sugiere y crea etiquetas desde el formulario (escenario 2, FR-003/004).
    client.force_login(p["colab"])
    html = client.get(reverse("learning:tag_suggest"), {"tag_q": "spark", "field": "tags"}).content.decode()
    assert "Spark" in html and "Crear" not in html
    html = client.get(reverse("learning:tag_suggest"), {"tag_q": "dbt"}).content.decode()
    assert "Crear «dbt»" in html
    form_html = client.get(reverse("learning:request_create") + f"?catalogo={catalog_course.pk}").content.decode()
    assert "data-tag-input" in form_html and "Big Data" in form_html  # precarga del catálogo
    assert client.get(reverse("learning:tag_list")).status_code == 403

    resp = client.post(reverse("learning:request_create") + f"?catalogo={catalog_course.pk}", {
        "catalogo": catalog_course.pk, "estimated_cost": "3500", "currency": "MXN",
        "start_date_planned": "2026-10-10", "end_date_planned": "2026-11-10", "justification": "x",
        "tags": ["Spark", "MLOps"], "action": "draft",
    })
    assert resp.status_code == 302
    req = catalog_course.requests.get()
    assert sorted(t.name for t in req.tags.all()) == ["MLOps", "Spark"]

    # Talento administra: lista, renombrar (htmx), desactivar y fusionar.
    client.force_login(p["talento"])
    assert "MLOps" in client.get(reverse("learning:tag_list")).content.decode()
    mlops = Tag.objects.get(key="mlops")
    resp = client.post(reverse("learning:tag_edit", args=[mlops.pk]), {"name": "ML Ops"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200 and "toast" in resp["HX-Trigger"] and "ML Ops" in resp.content.decode()
    resp = client.post(reverse("learning:tag_edit", args=[mlops.pk]), {"name": "spark"}, HTTP_HX_REQUEST="true")
    assert "fusiónalas" in resp.content.decode()
    client.post(reverse("learning:tag_toggle", args=[mlops.pk]))
    assert not Tag.objects.get(pk=mlops.pk).is_active
    spark, big = Tag.objects.get(key="spark"), Tag.objects.get(key="big data")
    client.post(reverse("learning:tag_merge", args=[big.pk]), {f"m{big.pk}-target": spark.pk})
    assert not Tag.objects.filter(pk=big.pk).exists()
    assert list(catalog_course.tags.all()) == [spark]

    # Catálogo: alta con etiquetas y enfoque; filtro por ficha de etiqueta.
    resp = client.post(reverse("learning:catalog_create"), {
        "name": "Fabric 101", "provider": "MS Learn", "url": "https://learn.microsoft.com/fabric", "kind": "PUNTUAL",
        "focus": "VERTICAL", "currency": "USD", "duration_hours": "1.5", "tag_names": ["KO", "Fabric"],
    })
    assert resp.status_code == 302
    new = CatalogCourse.objects.get(name="Fabric 101")
    assert (new.focus, str(new.duration_hours), new.created_by) == ("VERTICAL", "1.5", p["talento"])
    html = client.get(reverse("learning:catalog_list"), {"etiqueta": Tag.objects.get(key="ko").pk}).content.decode()
    assert "Fabric 101" in html and catalog_course.name not in html and "1.5 h" in html
