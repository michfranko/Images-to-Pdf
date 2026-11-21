"""
Estilos visuales modernos, minimalistas y profesionales para la aplicación
Images to PDF en PySide6 (Windows 10 / 11).
"""

MAIN_STYLESHEET = """
/* Reset y estilos generales */
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: #0f172a;
    background-color: #f8fafc;
}

/* Ventana Principal */
QMainWindow {
    background-color: #f8fafc;
}

/* Tarjetas y Contenedores (QGroupBox) */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 24px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
    color: #1e293b;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 6px;
    padding: 0 6px;
    background-color: #ffffff;
    color: #2563eb;
    border-radius: 4px;
}

/* Botones principales y genéricos */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 13px;
    color: #334155;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton:pressed {
    background-color: #e2e8f0;
    border-color: #64748b;
}

QPushButton:disabled {
    background-color: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
}

/* Botón de acción destacada (Primary) */
QPushButton#primaryButton {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 6px;
}

QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
    border-color: #1e40af;
}

QPushButton#primaryButton:pressed {
    background-color: #1e40af;
    border-color: #172554;
}

QPushButton#primaryButton:disabled {
    background-color: #93c5fd;
    border-color: #bfdbfe;
    color: #eff6ff;
}

/* Botón de Cancelar / Peligro */
QPushButton#dangerButton {
    background-color: #ef4444;
    border: 1px solid #dc2626;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
}

QPushButton#dangerButton:hover {
    background-color: #dc2626;
    border-color: #b91c1c;
}

QPushButton#dangerButton:pressed {
    background-color: #b91c1c;
}

QPushButton#dangerButton:disabled {
    background-color: #fca5a5;
    border-color: #fecaca;
    color: #ffffff;
}

/* Botones secundarios de éxito / apertura */
QPushButton#successButton {
    background-color: #10b981;
    border: 1px solid #059669;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
}

QPushButton#successButton:hover {
    background-color: #059669;
    border-color: #047857;
}

QPushButton#successButton:pressed {
    background-color: #047857;
}

/* Campos de Texto (QLineEdit) */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0f172a;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1.5px solid #2563eb;
    background-color: #ffffff;
}

QLineEdit:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Desplegables (QComboBox) */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #0f172a;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #94a3b8;
}

QComboBox:focus {
    border: 1.5px solid #2563eb;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
    padding: 4px;
}

/* Casillas de Verificación (QCheckBox) */
QCheckBox {
    spacing: 8px;
    font-weight: 500;
    color: #334155;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #2563eb;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
    image: none; /* Dibujado limpio */
}

/* Tabla de imágenes */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    outline: none;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #f1f5f9;
}

QTableWidget::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
    font-weight: 500;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1.5px solid #cbd5e1;
    padding: 8px 10px;
    text-align: left;
}

/* Barra de progreso */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 10px 18px;
    margin-right: 4px;
    color: #475569;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #2563eb;
    border-color: #cbd5e1;
}

QTabBar::tab:hover:!selected {
    background-color: #e8eef7;
    color: #1e293b;
}

QProgressBar {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background-color: #e2e8f0;
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    color: #1e293b;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

/* Barra de desplazamiento (QScrollBar) */
QScrollBar:vertical {
    border: none;
    background-color: #f8fafc;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Etiquetas (QLabel) */
QLabel {
    color: #334155;
}

QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}

QLabel#headerSubtitle {
    font-size: 13px;
    color: #64748b;
}

QLabel#resultBanner {
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    padding: 12px 16px;
    color: #15803d;
    font-size: 13px;
}
"""

