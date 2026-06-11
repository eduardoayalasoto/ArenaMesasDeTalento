# Accesos para revisión local

**URL:** http://127.0.0.1:8000
**Admin de Django (soporte):** http://127.0.0.1:8000/admin/

> Levantar el servidor:
> ```powershell
> $env:PYTHONIOENCODING='utf-8'
> .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
> ```

## Cuentas de prueba — contraseña para todas: `Arena2026!`

| Correo | Rol | Para qué sirve |
|---|---|---|
| `admin@arena-analytics.com` | Talento / superusuario | Administrar todo: usuarios, proyectos, cuestionarios, periodos, Impacto Arena, avance, exportes |
| `eduardo.ayala@arena-analytics.com` | Colaborador (ID · Mid) | Autoevaluación de Ownership y “Mis resultados” (tiene datos de ejemplo) |
| `hector@arena-analytics.com` | Lead de ID (lidera proyectos) | Validación de Ownership y captura de Entrega de Valor |
| `lorenzo@arena-analytics.com` | Director | Validar Entrega de Valor |

> ⚠️ Son credenciales de **desarrollo local**. Para producción se definen otras en Vercel (ver `docs/Deploy_Vercel.md`).

> 📸 **La foto es obligatoria:** al entrar con una cuenta que no sea superusuario, el sistema te llevará a **Mi perfil** a subir una foto antes de continuar (se muestra en el informe de resultados). El usuario `admin@` (superusuario) está exento.

## Dónde administrar
- **Proyectos** (crear/editar, líder, tipo de duración, equipo): menú **Proyectos** (rol Talento). Define si el proyecto es *finito* (con fecha de entrega) o *indefinido*; eso determina qué criterio de tiempo aparece en la Entrega de Valor.
- **Usuarios** (área/nivel/rol): menú **Usuarios**.
- **Cuestionarios** (editar/versionar): menú **Cuestionarios**.
- **Periodos** (abrir/cerrar): menú **Periodos**.
