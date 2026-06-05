"""
Script de una sola ejecución para inicializar las columnas del Google Sheet.

Uso:
    python scripts/init_sheet.py

Requisito: tener el archivo .env configurado en la raíz del proyecto.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.sheets import SheetsClient


def main():
    print("Conectando a Google Sheets...")
    client = SheetsClient()
    print("Conexion exitosa.")
    print("Verificando / creando headers...")
    client._ensure_headers()
    print("Listo. Las columnas estan creadas en tu hoja.")
    print("Abri Google Sheets y deberias ver la primera fila con todos los nombres de columna.")


if __name__ == "__main__":
    main()
