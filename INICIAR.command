#!/bin/bash
# Doble clic en este archivo (macOS) abre Terminal, instala lo necesario y abre la app.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

pause_on_error() {
    echo ""
    echo "Presiona Enter para cerrar esta ventana..."
    read -r _
}

trap 'echo ""; echo "Ocurrió un error. Revisa los mensajes de arriba."; pause_on_error; exit 1' ERR

echo "=============================================="
echo "  Herramienta de Detalle de Ventas — Panem"
echo "=============================================="
echo ""
echo "Ubicación: $SCRIPT_DIR"
echo ""

# --- 1. Git (necesario para actualizar e instalar dependencias desde GitHub) ---
if ! command -v git >/dev/null 2>&1; then
    echo ">> Paso 1/5: Se necesita Git."
    echo "   Si aparece un cuadro de diálogo de Apple, acepta instalar"
    echo "   las 'Herramientas de línea de comandos' (Xcode CLT)."
    xcode-select --install 2>/dev/null || true
    echo ""
    echo "   Cuando termine la instalación, vuelve a hacer doble clic en INICIAR.command."
    pause_on_error
    exit 1
fi
echo ">> Git: OK"

# --- 2. Actualización automática desde GitHub ---
# Se descarga siempre la última versión publicada en 'main'. Los archivos
# locales ignorados por git (secrets.env, .venv/) se conservan.
REPO_URL="https://github.com/ToxicFyre/marcelo-wansoft-processing-tool.git"
BRANCH="main"

update_from_github() {
    echo ">> Paso 2/5: Buscando actualizaciones en GitHub..."

    if [ ! -d ".git" ]; then
        echo "   Preparando actualizaciones automáticas (primera vez)..."
        git init -q
        git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"
    elif git remote get-url origin >/dev/null 2>&1; then
        git remote set-url origin "$REPO_URL"
    else
        git remote add origin "$REPO_URL"
    fi

    if ! git fetch -q origin "$BRANCH"; then
        echo "   Sin conexión o no se pudo actualizar; se usa la copia local."
        return 0
    fi

    if ! git checkout -f -B "$BRANCH" "origin/$BRANCH" -q; then
        echo "   No se pudo aplicar la actualización; se usa la copia local."
        return 0
    fi
    git reset --hard -q "origin/$BRANCH"
    echo "   Actualizado a la última versión (main)."
}

# Ejecuta la actualización una sola vez y vuelve a lanzar el script para que
# también se aplique una versión más reciente de INICIAR.command.
if [ "${SKIP_SELF_UPDATE:-}" != "1" ]; then
    update_from_github || true
    export SKIP_SELF_UPDATE=1
    exec /bin/bash "$0" "$@"
fi

# --- 3. Python 3.10+ ---
find_python() {
    for candidate in python3 python3.13 python3.12 python3.11 python3.10; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON="$(find_python || true)"

if [ -z "$PYTHON" ]; then
    echo ">> Paso 3/5: Instalando Python 3.10+ (puede tardar varios minutos)..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "   Instalando Homebrew primero..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -x /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
    brew install python@3.11
    if [ -x /opt/homebrew/bin/python3.11 ]; then
        PYTHON=/opt/homebrew/bin/python3.11
    elif [ -x /usr/local/bin/python3.11 ]; then
        PYTHON=/usr/local/bin/python3.11
    else
        PYTHON="$(find_python || true)"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo ""
    echo "ERROR: No se pudo instalar Python 3.10 o superior."
    echo "Descarga Python desde https://www.python.org/downloads/ e inténtalo de nuevo."
    pause_on_error
    exit 1
fi

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo ">> Python $PY_VERSION: OK"

# --- 4. Entorno virtual e instalación de paquetes ---
echo ">> Paso 4/5: Preparando entorno e instalando dependencias (primera vez: varios minutos)..."
if [ ! -d ".venv" ]; then
    "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip --quiet
python -m pip install -e . --quiet

if [ ! -f "secrets.env" ]; then
    if [ -f "secrets.env.example" ]; then
        cp secrets.env.example secrets.env
        echo ">> Se creó secrets.env desde el ejemplo."
        echo "   Para descargar de Wansoft en vivo, edita secrets.env con tus credenciales."
        echo "   Para subir Excel/CSV manualmente, no hace falta cambiar nada ahora."
    fi
fi

# --- 5. Abrir la aplicación ---
echo ">> Paso 5/5: Abriendo la aplicación en el navegador..."
echo ""
echo "   Para cerrar la app: vuelve a esta ventana y presiona Ctrl+C."
echo "   (No cierres esta ventana mientras uses la herramienta.)"
echo ""

streamlit run src/wansoft_tool/streamlit_app.py

echo ""
echo "Aplicación cerrada."
pause_on_error
