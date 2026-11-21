from pathlib import Path
import shutil
import subprocess
import sys

from build_exe import build_executable


def find_inno_compiler() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Users") / Path.home().name / r"AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    command = shutil.which("iscc")
    return Path(command).resolve() if command else None


def build_installer() -> None:
    root_dir = Path(__file__).resolve().parent
    build_executable()

    exe_path = root_dir / "dist" / "Images_to_PDF.exe"
    if not exe_path.exists():
        print("[ERROR] No se encontró el ejecutable generado.")
        sys.exit(1)

    iscc = find_inno_compiler()
    if not iscc:
        print("[ERROR] Inno Setup no está disponible.")
        sys.exit(1)

    print("\nCreando instalador con Inno Setup...")
    result = subprocess.run(
        [str(iscc), str(root_dir / "Images_to_PDF.iss")],
        cwd=str(root_dir),
    )
    if result.returncode != 0:
        sys.exit(result.returncode)

    installer = root_dir / "installer" / "Images_to_PDF_Setup.exe"
    print("=" * 60)
    print(" ¡Instalador completado con éxito!")
    print(f"Instalador generado en:\n{installer}\n")


if __name__ == "__main__":
    build_installer()
