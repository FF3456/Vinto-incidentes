# SIRIMA Vinto — Sistema de Reporte de Incidentes Medio Ambientales

MVP de la **Segunda Entrega** · Taller de Programación · Universidad Adventista de Bolivia  
Python 3.11+ · NiceGUI · SQLAlchemy/SQLite · Arquitectura Hexagonal (monolito modular)

## Ejecución rápida
```bash
python -m venv .venv && .\.venv\Scripts\Activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                                          # http://localhost:8082
```
La primera ejecución crea `data/vinto.db`, el catálogo de categorías, cuentas y 12 reportes de demostración.

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@vinto.gob.bo | Vinto2026 |
| Funcionario municipal | funcionario@vinto.gob.bo | Vinto2026 |
| Responsable de atención | responsable@vinto.gob.bo / responsable2@vinto.gob.bo | Vinto2026 |
| Ciudadano | vecino@vinto.gob.bo | Vinto2026 |

El ciudadano también puede reportar **sin cuenta** y consultar su reporte con el código `VINTO-AAAA-NNNN`.

## Variables de entorno (opcionales)
`PORT` (8080) · `VINTO_DB` (sqlite:///data/vinto.db; admite PostgreSQL) · `VINTO_EVIDENCIAS` · `VINTO_MAPA` (`osm`|`carto`) ·
`VINTO_DEMO` (`0` = sin cuentas ni datos de ejemplo, para producción) · `VINTO_SECRETO` (clave de sesión: **cámbiela**).

## Pruebas
```bash
pytest -q                                                    # 89 pruebas
pytest --cov=domain --cov=application --cov=infrastructure   # ≈95 % de cobertura
```
## Demostración automatizada + capturas (opcional)
```bash
pip install playwright && playwright install chromium
python main.py &            # con base limpia
python tools/capturas.py    # recorre los 10 RF con los 4 roles → docs/capturas/
```
## Estructura
```
domain/          entidades, objetos de valor, Factory, políticas RBAC y PUERTOS (interfaces)
application/     casos de uso (orquestan el dominio; no conocen frameworks)
infrastructure/  adaptadores: SQLAlchemy, mapas (OSM/Carto), archivos, hashing, memoria
presentation/    NiceGUI: páginas y componentes
bootstrap.py     raíz de composición (único lugar que elige implementaciones)
tests/           PyTest: dominio, casos de uso, integración, arquitectura
```
> Nota: las zonas (Zona Central, Norte, Sur…) y el área de cobertura son **referenciales**; deben ajustarse con la cartografía oficial.
