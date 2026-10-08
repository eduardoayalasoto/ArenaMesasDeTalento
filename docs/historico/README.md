# Índice de documentación — Mesa de Talento (Arena Analytics)

Guía rápida de qué es cada documento y en qué orden leerlos.

## 📌 Empieza aquí (estado y operación del sistema)
| Documento | Para qué |
|---|---|
| **`CONTEXTO_Sistema.md`** | **Lee esto primero.** Panorama completo del sistema actual: arquitectura, modelos, flujos, roles, pantallas, comandos, peculiaridades. |
| **`Deploy_Vercel.md`** | Desplegar en Vercel + Neon: variables de entorno, migraciones, **respaldos y restauración** (snapshots / Neon). |
| **`Progreso_Desarrollo.md`** | Bitácora cronológica e historial por fase (qué se hizo y cuándo). |
| **`Plan_Desarrollo_Webapp_Evaluaciones.md`** | Plan/diseño **original** (referencia histórica). El estado real vive en `CONTEXTO_Sistema.md`. |

## 📖 Reglas de negocio (fuente de verdad)
| Documento | Para qué |
|---|---|
| **`KB_Modelo_Desempeno_2026.md`** | Fuente única de las reglas (RN‑xx), escalas, fórmulas, permisos. Todo lo demás se deriva de aquí. |


## 🗃️ Insumos originales (históricos — base del KB y de los cuestionarios)
| Carpeta / archivo | Notas |
|---|---|
| `Modelos/2026 Modelo de desempeño analítica.md` y `… Junta informativa.md` | Material original del modelo; ya **consolidado** en el KB. |
| `Modelos/Ponderación.md` | Pesos por nivel; ya en el KB y en `seed_catalogs`. |
| `Modelos/Lista de colaboradores Analítica 2026.md` | **Histórico.** La lista **vigente** de usuarios es `Modelos/usuarios.csv` (la que importa `manage.py import_csv_users`). |
| `Checklists/` | Texto original de los 16 cuestionarios de Ownership + Entrega de Valor; ya cargados como datos (`fixtures/questionnaires/` → `seed_questionnaires`). |

## 🔒 Local / privado (NO está en el repo)
- `CREDENCIALES.md` — accesos de prueba locales.
- `neon.md` — cadena de conexión de Neon.
- `../backups/` — snapshots de la BD.

> Regla práctica: para **entender el sistema**, `CONTEXTO_Sistema.md`. Para **desplegar/operar**, `Deploy_Vercel.md`. Para **las reglas**, el `KB`. Lo demás es histórico/insumo.
