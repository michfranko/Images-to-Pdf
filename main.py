"""
Punto de entrada principal para la aplicación Images to PDF Desktop.
Inicializa QApplication, aplica los estilos visuales modernos y muestra la ventana principal.
"""

import sys
from main_window import MainWindow
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from styles import MAIN_STYLESHEET


def main() -> None:
    # Soporte para pantallas de alta densidad de píxeles (High DPI)
    # Qt6 gestiona High DPI de forma nativa por defecto.

    app = QApplication(sys.argv)
    app.setApplicationName("Images to PDF")
    app.setApplicationDisplayName("Images to PDF")
    app.setOrganizationName("Antigravity")

    # Aplicar hoja de estilos QSS
    app.setStyleSheet(MAIN_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

