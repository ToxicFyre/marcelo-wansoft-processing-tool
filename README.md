# Herramienta de Detalle de Ventas — Panem

Aplicación para que Marcelo analice **detalle de ventas**: unifica productos (conchas, café refill, chilaquiles, Uber/Rappi/DiDi), recomienda **ventas cruzadas** y muestra el análisis **80/20** con descarga a Excel.

## Inicio rápido (Mac — Marcelo)

1. Descomprime el ZIP que te enviaron en cualquier carpeta (por ejemplo Escritorio).
2. Haz **doble clic** en **`INICIAR.command`**.
   - Si macOS dice que no puede abrirlo: clic derecho → **Abrir** → **Abrir** (solo la primera vez).
3. La primera vez, Terminal instalará Python (si hace falta), las dependencias y abrirá el navegador solo.
4. **Cada vez que abras la app se descarga automáticamente la última versión** publicada en GitHub, así que siempre usas el código más reciente. Necesitas conexión a internet; si estás sin conexión, se usa la copia local que ya tenías.
5. Para cerrar la app: vuelve a la ventana de Terminal y presiona **Ctrl+C**.

> Tus credenciales (`secrets.env`) y el entorno instalado (`.venv/`) **no** se borran al actualizar.

**Incluir en el ZIP para Marcelo:** todo el proyecto **sin** la carpeta `.venv`. No hace falta incluir la carpeta `.git`; `INICIAR.command` conecta con GitHub solo la primera vez que se ejecuta.

## Requisitos

- Python 3.10 o superior

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Abrir la aplicación

```bash
streamlit run src/wansoft_tool/streamlit_app.py
```

Se abrirá en el navegador (por defecto `http://localhost:8501`).

## Cómo usar

1. **Subir Excel**: sube uno o más `Detail_*.xlsx` (Detalle de Ventas), luego **Cargar datos**. El sistema los limpia y enriquece automáticamente.

2. **Combinar Uber/Rappi/DiDi**: activado por defecto. Une ventas de delivery con el mismo producto de tienda (ej. `CONCHA UBER` + chocolate = `concha chocolate`).

3. **Pestañas**
   - **Resumen**: ingresos, tickets, productos.
   - **Ventas cruzadas**: tres oportunidades confiables y sugerencias por producto.
   - **Top productos (80/20)**: productos que concentran ~80% de ingresos.
   - **Detalle enriquecido**: tabla completa.
   - **Descargar**: Excel de ventas cruzadas, resumen 80/20 o detalle completo.

Las recomendaciones de venta cruzada comparan productos del mismo ticket y
descartan asociaciones con poca evidencia. “También aparece en 20%” describe
los datos históricos; no garantiza que ofrecer el producto cause la compra.
La tabla por producto muestra los tickets del producto y los tickets con ambos
para que la confianza sea intuitiva (confianza = tickets con ambos ÷ tickets del
producto). Consulta [el método y sus métricas](docs/CROSS_SELLING_METHOD.md) para
interpretar confianza, afinidad y el piso seguro (mínimo conservador).

## Validación (desarrolladores)

```bash
pytest
ruff check src tests --exclude .venv
ruff format --check src tests --exclude .venv
mypy src
archbrace check .
```

## Fixtures de prueba

Los tests usan CSV en `tests/fixtures/`. Para regenerarlos (maintainers):

```bash
python tests/bootstrap_fixtures.py
pytest tests/test_fixtures_provenance.py
```

## Estructura

- `config/modifier_products.yaml` — reglas de productos (conchas, café, chilaquiles)
- `src/wansoft_tool/` — lógica de enriquecimiento, análisis y UI
- `sucursales.json` — códigos de sucursal
