"""
Script de compilación y empaquetado para generar el ejecutable autónomo
Images_to_PDF.exe mediante PyInstaller en Windows 10 y 11.
"""

from pathlib import Path
import subprocess
import sys


def build_executable() -> None:
    root_dir = Path(__file__).resolve().parent
    entry_point = root_dir / "main.py"
    output_name = "Images_to_PDF"

    print("=" * 60)
    print(" Compilando Images to PDF a ejecutable de Windows (.exe)")
    print("=" * 60)
    print(f"Directorio base: {root_dir}")
    print(f"Punto de entrada: {entry_point}")

    # Argumentos de PyInstaller
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",  # Sin ventana de terminal negra de fondo
        "--onefile",  # Genera un único archivo ejecutable independiente
        f"--name={output_name}",
        "--clean",
        # Recopilación de dependencias críticas
        "--collect-data=reportlab",
        "--collect-submodules=reportlab",
        "--collect-submodules=pypdf",
        "--collect-submodules=pypdf",
        "--collect-submodules=PIL",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        str(entry_point),
    ]

    print("\nEjecutando comando:")
    print(" ".join(args))
    print("\nProcesando... Por favor espera unos momentos.\n")

    result = subprocess.run(args, cwd=str(root_dir))
    if result.returncode == 0:
        exe_path = root_dir / "dist" / f"{output_name}.exe"
        print("\n" + "=" * 60)
        print(" ¡Compilación completada con éxito!")
        print("=" * 60)
        print(f"Ejecutable generado en:\n{exe_path}\n")
    else:
        print("\n[ERROR] La compilación falló. Código de salida:", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_executable()

