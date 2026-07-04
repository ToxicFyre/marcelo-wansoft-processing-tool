# Herramienta de Detalle de Ventas — Panem

Aplicación para que Marcelo analice **detalle de ventas** de Wansoft: descarga datos, unifica productos (conchas, café refill, chilaquiles, Uber/Rappi/DiDi) y muestra el análisis **80/20** con descarga a Excel.

## Inicio rápido (Mac — Marcelo)

1. Descomprime el ZIP que te enviaron en cualquier carpeta (por ejemplo Escritorio).
2. Haz **doble clic** en **`INICIAR.command`**.
   - Si macOS dice que no puede abrirlo: clic derecho → **Abrir** → **Abrir** (solo la primera vez).
3. La primera vez, Terminal instalará Python (si hace falta), las dependencias y abrirá el navegador solo.
4. Para cerrar la app: vuelve a la ventana de Terminal y presiona **Ctrl+C**.

**Incluir en el ZIP para Marcelo:** todo el proyecto **sin** la carpeta `.venv`. Opcional: un `secrets.env` ya configurado con credenciales Wansoft (si usará descarga en vivo).

## Requisitos

- Python 3.10 o superior
- Credenciales Wansoft (solo si usas descarga en vivo)

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configurar credenciales

```bash
cp secrets.env.example secrets.env
```

Edita `secrets.env` con los valores que te proporcione el administrador:

| Variable | Descripción |
|----------|-------------|
| `WS_BASE` | URL del POS Wansoft |
| `WS_USER` | Usuario Wansoft |
| `WS_PASS` | Contraseña Wansoft |

Si solo subes archivos CSV, no necesitas credenciales.

## Abrir la aplicación

```bash
streamlit run src/wansoft_tool/streamlit_app.py
```

Se abrirá en el navegador (por defecto `http://localhost:8501`).

## Cómo usar

1. **Subir Excel**: sube uno o más `Detail_*.xlsx` descargados desde Wansoft (Detalle de Ventas), luego **Cargar datos**. El sistema los limpia y enriquece automáticamente.

2. **Combinar Uber/Rappi/DiDi**: activado por defecto. Une ventas de delivery con el mismo producto de tienda (ej. `CONCHA UBER` + chocolate = `concha chocolate`).

3. **Pestañas**
   - **Resumen**: ingresos, tickets, productos.
   - **Top productos (80/20)**: productos que concentran ~80% de ingresos.
   - **Detalle enriquecido**: tabla completa.
   - **Descargar**: Excel del resumen 80/20 o del detalle completo.

## Validación (desarrolladores)

```bash
pytest
ruff check src tests --exclude .venv
ruff format --check src tests --exclude .venv
mypy src
archbrace check src
```

## Fixtures de prueba

Los tests usan CSV reales en `tests/fixtures/`, generados **solo** con descarga
en vivo desde Wansoft (no copies desde otros repos).

```bash
# Requiere secrets.env válido (WS_BASE, WS_USER, WS_PASS)
python tests/bootstrap_fixtures.py
pytest tests/test_fixtures_provenance.py   # verifica procedencia live
```

Si el bootstrap falla con error de autenticación, corrige `secrets.env` y
reintenta. **No sustituyas los fixtures por CSV locales** — eso invalida las
pruebas de regresión.

## Estructura

- `config/modifier_products.yaml` — reglas de productos (conchas, café, chilaquiles)
- `src/wansoft_tool/` — lógica de enriquecimiento, análisis y UI
- `sucursales.json` — códigos de sucursal para Wansoft
