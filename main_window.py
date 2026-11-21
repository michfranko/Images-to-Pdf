"""
Ventana principal de la aplicación Images to PDF en PySide6.
Proporciona una interfaz moderna, minimalista y profesional para gestionar
la lista de imágenes, previsualizar miniaturas, configurar el PDF y realizar
la conversión en segundo plano.
"""

import os
from pathlib import Path
import sys
from typing import Any

from image_handler import (
    SUPPORTED_EXTENSIONS,
    ImageItem,
    find_images_in_folder,
    natural_sort_key,
    read_image_metadata,
)
from pdf_generator import unique_output_path, valid_pdf_name
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from workers import ConversionWorker, PdfMergeWorker, ThumbnailLoaderWorker


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación de escritorio."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Images to PDF — Calidad Profesional")
        self.resize(1380, 900)
        self.setMinimumSize(1180, 720)

        # Habilitar arrastrar y soltar (Drag and Drop)
        self.setAcceptDrops(True)

        # Estado interno
        self.image_items: list[ImageItem] = []
        self.source_folder: Path | None = None
        self.destination_folder: Path | None = None
        self.last_generated_pdf: Path | None = None
        self.pdf_paths: list[Path] = []

        # Trabajadores en segundo plano
        self.conversion_worker: ConversionWorker | None = None
        self.pdf_merge_worker: PdfMergeWorker | None = None
        self.thumb_worker: ThumbnailLoaderWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """Construye todos los componentes y paneles de la interfaz gráfica."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Cabecera (Header)
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)

        title_label = QLabel("Images to PDF", self)
        title_label.setObjectName("headerTitle")
        subtitle_label = QLabel(
            "Conversión de imágenes a PDF con máxima fidelidad visual, "
            "inserción directa sin pérdida y proporciones originales.",
            self,
        )
        subtitle_label.setObjectName("headerSubtitle")

        header_text_layout.addWidget(title_label)
        header_text_layout.addWidget(subtitle_label)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Separador horizontal sutil
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0; margin-bottom: 4px;")
        main_layout.addWidget(sep)

        # 2. Área principal dividida (Splitter Horizontal: Panel Izquierdo / Panel Derecho)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- PANEL IZQUIERDO: Selección y Lista de Imágenes ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Botones de selección y manipulación
        toolbar_group = QGroupBox("Gestión de Imágenes")
        toolbar_layout = QHBoxLayout(toolbar_group)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        toolbar_layout.setSpacing(8)

        self.btn_select_folder = QPushButton("Seleccionar carpeta")
        self.btn_select_folder.setIcon(
            self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton)
        )
        self.btn_select_folder.clicked.connect(self._on_select_folder)

        self.btn_add_files = QPushButton("Añadir imágenes")
        self.btn_add_files.setIcon(
            self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon)
        )
        self.btn_add_files.clicked.connect(self._on_add_individual_files)

        self.btn_move_up = QPushButton("▲ Subir")
        self.btn_move_up.clicked.connect(self._on_move_up)

        self.btn_move_down = QPushButton("▼ Bajar")
        self.btn_move_down.clicked.connect(self._on_move_down)

        self.btn_remove_selected = QPushButton("Eliminar")
        self.btn_remove_selected.clicked.connect(self._on_remove_selected)

        self.btn_clear_list = QPushButton("Limpiar todo")
        self.btn_clear_list.clicked.connect(self._on_clear_list)

        toolbar_layout.addWidget(self.btn_select_folder)
        toolbar_layout.addWidget(self.btn_add_files)
        toolbar_layout.addWidget(self.btn_move_up)
        toolbar_layout.addWidget(self.btn_move_down)
        toolbar_layout.addWidget(self.btn_remove_selected)
        toolbar_layout.addWidget(self.btn_clear_list)

        left_layout.addWidget(toolbar_group)

        # Tabla de imágenes
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["#", "Miniatura", "Archivo", "Dimensiones", "Formato"]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setIconSize(self.table.iconSize())

        # Configurar anchos de columna
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 75)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )

        left_layout.addWidget(self.table)

        # Etiqueta de resumen de lista
        self.lbl_list_summary = QLabel(
            "Arrastra imágenes aquí o pulsa 'Seleccionar carpeta'."
        )
        self.lbl_list_summary.setStyleSheet("color: #64748B; font-size: 12px;")
        left_layout.addWidget(self.lbl_list_summary)

        splitter.addWidget(left_widget)

        # --- PANEL DERECHO: Configuración del Documento ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(12)

        # Configuración del Documento
        config_group = QGroupBox("Configuración del Documento")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)

        # Nombre del PDF
        lbl_name = QLabel("Nombre del archivo PDF:")
        self.txt_pdf_name = QLineEdit("documento_combinado")
        self.txt_pdf_name.setPlaceholderText("Nombre del archivo sin .pdf")
        config_layout.addWidget(lbl_name)
        config_layout.addWidget(self.txt_pdf_name)

        # Carpeta de destino
        lbl_dest = QLabel("Carpeta de destino:")
        dest_box = QHBoxLayout()
        self.txt_dest_folder = QLineEdit()
        self.txt_dest_folder.setPlaceholderText(
            "Ubicación donde guardar el PDF generado"
        )
        self.btn_browse_dest = QPushButton("Examinar...")
        self.btn_browse_dest.clicked.connect(self._on_browse_destination)
        self.btn_same_as_src = QPushButton("Origen")
        self.btn_same_as_src.setToolTip(
            "Guardar en la misma carpeta que las imágenes de origen"
        )
        self.btn_same_as_src.clicked.connect(self._on_same_as_source)

        dest_box.addWidget(self.txt_dest_folder)
        dest_box.addWidget(self.btn_browse_dest)
        dest_box.addWidget(self.btn_same_as_src)
        config_layout.addWidget(lbl_dest)
        config_layout.addLayout(dest_box)

        # Opciones de búsqueda y orden
        opts_grid = QGridLayout()
        self.chk_natural_sort = QCheckBox("Ordenamiento natural (ej. 1, 2, 10)")
        self.chk_natural_sort.setChecked(True)
        self.chk_natural_sort.stateChanged.connect(self._on_sort_option_changed)

        self.chk_recursive = QCheckBox("Incluir subcarpetas al seleccionar")
        self.chk_recursive.setChecked(False)

        self.chk_overwrite = QCheckBox("Sobrescribir si ya existe")
        self.chk_overwrite.setChecked(False)

        opts_grid.addWidget(self.chk_natural_sort, 0, 0)
        opts_grid.addWidget(self.chk_recursive, 0, 1)
        opts_grid.addWidget(self.chk_overwrite, 1, 0, 1, 2)
        config_layout.addLayout(opts_grid)

        # Opciones de Formato de Página
        page_grid = QGridLayout()

        lbl_page_size = QLabel("Tamaño de página:")
        self.cmb_page_size = QComboBox()
        self.cmb_page_size.addItem(
            "Proporcional a la imagen (Dimensiones originales)", "proportional"
        )
        self.cmb_page_size.addItem("Formato A4 estándar (210 × 297 mm)", "a4")

        lbl_orientation = QLabel("Orientación:")
        self.cmb_orientation = QComboBox()
        self.cmb_orientation.addItem("Automática según cada imagen", "auto")
        self.cmb_orientation.addItem("Vertical fija (Portrait)", "portrait")
        self.cmb_orientation.addItem("Horizontal fija (Landscape)", "landscape")

        lbl_margin = QLabel("Márgenes:")
        self.cmb_margin = QComboBox()
        self.cmb_margin.addItem("Sin márgenes (0 mm / borde a borde)", 0.0)
        self.cmb_margin.addItem("Estrecho (5 mm)", 5.0)
        self.cmb_margin.addItem("Estándar (10 mm)", 10.0)
        self.cmb_margin.addItem("Ancho (15 mm)", 15.0)
        self.cmb_margin.addItem("Personalizado (20 mm)", 20.0)

        page_grid.addWidget(lbl_page_size, 0, 0)
        page_grid.addWidget(self.cmb_page_size, 0, 1)
        page_grid.addWidget(lbl_orientation, 1, 0)
        page_grid.addWidget(self.cmb_orientation, 1, 1)
        page_grid.addWidget(lbl_margin, 2, 0)
        page_grid.addWidget(self.cmb_margin, 2, 1)
        page_grid.setColumnMinimumWidth(0, 145)
        page_grid.setColumnStretch(1, 1)

        config_layout.addLayout(page_grid)
        config_layout.addStretch()

        # Union de archivos PDF
        merge_group = QGroupBox("Unir varios archivos PDF")
        merge_layout = QVBoxLayout(merge_group)
        merge_layout.setSpacing(8)

        merge_toolbar = QHBoxLayout()
        self.btn_add_pdfs = QPushButton("Añadir PDFs")
        self.btn_add_pdfs.clicked.connect(self._on_add_pdf_files)
        self.btn_pdf_up = QPushButton("▲ Subir")
        self.btn_pdf_up.clicked.connect(self._on_pdf_move_up)
        self.btn_pdf_down = QPushButton("▼ Bajar")
        self.btn_pdf_down.clicked.connect(self._on_pdf_move_down)
        self.btn_remove_pdfs = QPushButton("Eliminar")
        self.btn_remove_pdfs.clicked.connect(self._on_remove_pdf_files)
        self.btn_clear_pdfs = QPushButton("Limpiar")
        self.btn_clear_pdfs.clicked.connect(self._on_clear_pdf_files)

        merge_toolbar.addWidget(self.btn_add_pdfs)
        merge_toolbar.addWidget(self.btn_pdf_up)
        merge_toolbar.addWidget(self.btn_pdf_down)
        merge_toolbar.addWidget(self.btn_remove_pdfs)
        merge_toolbar.addWidget(self.btn_clear_pdfs)
        merge_layout.addLayout(merge_toolbar)

        self.pdf_table = QTableWidget(0, 3)
        self.pdf_table.setHorizontalHeaderLabels(["#", "Archivo PDF", "Ubicación"])
        self.pdf_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.pdf_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.pdf_table.verticalHeader().setVisible(False)
        pdf_header = self.pdf_table.horizontalHeader()
        pdf_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        pdf_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        pdf_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.pdf_table.setMinimumHeight(260)
        merge_layout.addWidget(self.pdf_table)

        merge_name_layout = QGridLayout()
        merge_name_layout.addWidget(QLabel("Nombre del PDF unido:"), 0, 0)
        self.txt_merge_name = QLineEdit("documento_unido")
        merge_name_layout.addWidget(self.txt_merge_name, 0, 1)

        self.btn_merge_pdfs = QPushButton("UNIR PDFS")
        self.btn_merge_pdfs.setObjectName("primaryButton")
        self.btn_merge_pdfs.clicked.connect(self._on_merge_pdfs)
        merge_name_layout.addWidget(self.btn_merge_pdfs, 1, 0, 1, 2)
        merge_layout.addLayout(merge_name_layout)
        merge_layout.addStretch()

        # Panel de Resultados
        self.results_group = QGroupBox("Resultados de la Conversión")
        self.results_layout = QVBoxLayout(self.results_group)
        self.results_layout.setSpacing(8)

        self.lbl_result_info = QLabel("Aún no se ha realizado ninguna conversión.")
        self.lbl_result_info.setStyleSheet("color: #64748B; font-size: 12px;")
        self.lbl_result_info.setWordWrap(True)
        self.lbl_result_info.setMinimumHeight(90)
        self.results_layout.addWidget(self.lbl_result_info)

        res_btn_layout = QHBoxLayout()
        self.btn_open_pdf = QPushButton("Abrir documento PDF")
        self.btn_open_pdf.setObjectName("successButton")
        self.btn_open_pdf.setEnabled(False)
        self.btn_open_pdf.clicked.connect(self._on_open_pdf)

        self.btn_open_folder = QPushButton("Abrir carpeta de destino")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self._on_open_dest_folder)

        res_btn_layout.addWidget(self.btn_open_pdf)
        res_btn_layout.addWidget(self.btn_open_folder)
        self.results_layout.addLayout(res_btn_layout)
        self.results_layout.addStretch()

        # Pestañas independientes para evitar paneles apretados
        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName("mainTabs")
        self.right_tabs.addTab(config_group, "Configuración")
        self.right_tabs.addTab(merge_group, "Unir PDFs")
        self.right_tabs.addTab(self.results_group, "Resultados")
        right_layout.addWidget(self.right_tabs)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter, 1)

        # 3. Panel Inferior de Conversión y Progreso
        action_group = QGroupBox("Panel de Conversión")
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(10)

        top_action_layout = QHBoxLayout()
        self.btn_convert = QPushButton("CONVERTIR A PDF")
        self.btn_convert.setObjectName("primaryButton")
        self.btn_convert.clicked.connect(self._on_start_conversion)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_conversion)

        top_action_layout.addWidget(self.btn_convert, 3)
        top_action_layout.addWidget(self.btn_cancel, 1)
        action_layout.addLayout(top_action_layout)

        # Barra de progreso y estado
        prog_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Listo para convertir (0%)")

        self.lbl_current_status = QLabel("Esperando inicio.")
        self.lbl_current_status.setStyleSheet(
            "color: #475569; font-size: 12px; font-weight: 500;"
        )

        prog_layout.addWidget(self.progress_bar, 3)
        prog_layout.addWidget(self.lbl_current_status, 2)
        action_layout.addLayout(prog_layout)

        main_layout.addWidget(action_group)

    # =========================================================================
    # EVENTOS DRAG & DROP
    # =========================================================================
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Acepta el arrastre si contiene URLs de archivos o carpetas."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Gestiona el soltado de archivos o carpetas en la ventana."""
        urls = event.mimeData().urls()
        paths: list[Path] = [
            Path(u.toLocalFile()) for u in urls if u.isLocalFile()
        ]

        folder_candidates = [p for p in paths if p.is_dir()]
        file_candidates = [
            p
            for p in paths
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        pdf_candidates = [
            p for p in paths if p.is_file() and p.suffix.lower() == ".pdf"
        ]

        if folder_candidates:
            # Si se soltó una carpeta, cargar su contenido
            self._load_from_folder(
                folder_candidates[0], self.chk_recursive.isChecked()
            )
        elif pdf_candidates:
            self._append_pdf_paths(pdf_candidates)
        elif file_candidates:
            # Si se soltaron archivos sueltos
            self._append_image_paths(file_candidates)

        event.acceptProposedAction()

    # =========================================================================
    # CARGA Y GESTIÓN DE IMÁGENES
    # =========================================================================
    def _on_select_folder(self) -> None:
        """Abre el explorador para seleccionar una carpeta completa de imágenes."""
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de imágenes",
            str(self.source_folder or Path.home()),
        )
        if selected:
            folder = Path(selected)
            self._load_from_folder(folder, self.chk_recursive.isChecked())

    def _load_from_folder(self, folder: Path, recursive: bool) -> None:
        """Carga los archivos de imagen encontrados en la carpeta."""
        self.source_folder = folder
        if not self.destination_folder:
            self.destination_folder = folder
            self.txt_dest_folder.setText(str(folder))

        paths = find_images_in_folder(
            folder,
            recursive=recursive,
            natural_order=self.chk_natural_sort.isChecked(),
        )

        if not paths:
            QMessageBox.information(
                self,
                "Sin imágenes compatibles",
                f"No se encontraron imágenes en:\n{folder}\n\n"
                f"Formatos soportados: {', '.join(sorted(set(SUPPORTED_EXTENSIONS.values())))}",
            )
            return

        self._populate_images(paths)

    def _on_add_individual_files(self) -> None:
        """Abre el explorador para agregar archivos de imagen específicos."""
        ext_filter = "Imágenes (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif *.ico);;Todos los archivos (*.*)"
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar imágenes individuales",
            str(self.source_folder or Path.home()),
            ext_filter,
        )
        if selected_files:
            paths = [Path(p) for p in selected_files]
            if not self.destination_folder and paths:
                self.destination_folder = paths[0].parent
                self.txt_dest_folder.setText(str(self.destination_folder))
            self._append_image_paths(paths)

    def _populate_images(self, paths: list[Path]) -> None:
        """Reemplaza la lista actual con una nueva colección de rutas."""
        self._cancel_thumbnail_loader()
        self.image_items.clear()
        self.table.setRowCount(0)
        self._append_image_paths(paths)

    def _append_image_paths(self, paths: list[Path]) -> None:
        """Agrega nuevas rutas de imagen a la lista y dispara la carga de

        miniaturas.
        """
        existing_paths = {item.path.resolve() for item in self.image_items}
        new_unique = [p for p in paths if p.resolve() not in existing_paths]

        if not new_unique:
            return

        start_row = len(self.image_items)
        tasks: list[tuple[int, Path]] = []

        for i, p in enumerate(new_unique):
            row_idx = start_row + i
            # Placeholder temporal rápido
            dummy_item = ImageItem(
                path=p,
                filename=p.name,
                extension=p.suffix.lower(),
                format_label=SUPPORTED_EXTENSIONS.get(
                    p.suffix.lower(), p.suffix.upper()
                ),
                width=0,
                height=0,
                visual_width=0,
                visual_height=0,
                dpi_x=150.0,
                dpi_y=150.0,
                exif_orientation=1,
                file_size_bytes=0,
                is_valid=True,
            )
            self.image_items.append(dummy_item)
            tasks.append((row_idx, p))

            # Añadir fila en la tabla
            self.table.insertRow(row_idx)
            self.table.setRowHeight(row_idx, 60)

            item_num = QTableWidgetItem(f"#{row_idx + 1}")
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, item_num)

            # Miniatura provisional
            thumb_label = QLabel("Cargando...")
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_label.setStyleSheet("color: #94A3B8; font-size: 10px;")
            self.table.setCellWidget(row_idx, 1, thumb_label)

            item_name = QTableWidgetItem(p.name)
            self.table.setItem(row_idx, 2, item_name)

            item_dims = QTableWidgetItem("Leyendo...")
            item_dims.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, item_dims)

            item_fmt = QTableWidgetItem(dummy_item.format_label)
            item_fmt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 4, item_fmt)

        self._update_list_summary()

        # Iniciar carga asíncrona de miniaturas y metadatos
        self._start_thumbnail_loader(tasks)

    def _start_thumbnail_loader(self, tasks: list[tuple[int, Path]]) -> None:
        """Inicia el hilo de carga de miniaturas en segundo plano."""
        self.thumb_worker = ThumbnailLoaderWorker(tasks)
        self.thumb_worker.item_loaded.connect(self._on_thumbnail_item_loaded)
        self.thumb_worker.start()

    def _cancel_thumbnail_loader(self) -> None:
        """Cancela y espera de forma segura el hilo de carga previo."""
        if self.thumb_worker and self.thumb_worker.isRunning():
            self.thumb_worker.cancel()
            self.thumb_worker.wait(1000)
            self.thumb_worker = None

    def _on_thumbnail_item_loaded(
        self, row_idx: int, item: ImageItem, thumb_bytes: bytes
    ) -> None:
        """Callback cuando una miniatura y sus metadatos se cargan en segundo

        plano.
        """
        if 0 <= row_idx < len(self.image_items):
            self.image_items[row_idx] = item

            # Actualizar miniatura
            if thumb_bytes:
                pix = QPixmap()
                pix.loadFromData(thumb_bytes)
                thumb_label = QLabel()
                thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb_label.setPixmap(pix)
                self.table.setCellWidget(row_idx, 1, thumb_label)
            else:
                err_label = QLabel("Error")
                err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                err_label.setStyleSheet("color: #DC2626; font-size: 10px;")
                self.table.setCellWidget(row_idx, 1, err_label)

            # Actualizar dimensiones y formato
            dims_item = self.table.item(row_idx, 3)
            if dims_item:
                dims_item.setText(
                    item.dimensions_display if item.is_valid else "Dañado"
                )

            fmt_item = self.table.item(row_idx, 4)
            if fmt_item:
                fmt_item.setText(
                    f"{item.format_label} ({item.file_size_display})"
                )

        self._update_list_summary()

    def _update_list_summary(self) -> None:
        """Actualiza la etiqueta con la cantidad de imágenes y tamaño total."""
        count = len(self.image_items)
        if count == 0:
            self.lbl_list_summary.setText(
                "Arrastra imágenes aquí o pulsa 'Seleccionar carpeta'."
            )
            return

        total_bytes = sum(item.file_size_bytes for item in self.image_items)
        val = float(total_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if val < 1024 or unit == "GB":
                size_str = (
                    f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
                )
                break
            val /= 1024
        else:
            size_str = f"{val:.1f} GB"

        self.lbl_list_summary.setText(
            f"<b>{count} imágenes listas</b> para incorporar al PDF · Tamaño acumulado: {size_str}"
        )

    def _renumber_table(self) -> None:
        """Reasigna los números de orden (#1, #2, ...) en la tabla."""
        for row in range(self.table.rowCount()):
            num_item = self.table.item(row, 0)
            if num_item:
                num_item.setText(f"#{row + 1}")

    # =========================================================================
    # MANIPULACIÓN DE LISTA (ORDEN Y BORRADO)
    # =========================================================================
    def _on_sort_option_changed(self) -> None:
        """Reordena la lista actual según el estado del ordenamiento natural."""
        if not self.image_items:
            return

        is_natural = self.chk_natural_sort.isChecked()
        if is_natural:
            self.image_items.sort(key=lambda item: natural_sort_key(item.filename))
        else:
            self.image_items.sort(
                key=lambda item: (item.filename.casefold(), item.filename)
            )

        # Reconstruir la tabla manteniendo los metadatos ya cargados
        paths = [item.path for item in self.image_items]
        self._populate_images(paths)

    def _on_move_up(self) -> None:
        """Mueve las filas seleccionadas una posición hacia arriba."""
        selected_rows = sorted(
            [idx.row() for idx in self.table.selectionModel().selectedRows()]
        )
        if not selected_rows or selected_rows[0] == 0:
            return

        for row in selected_rows:
            # Intercambiar en la lista
            self.image_items[row - 1], self.image_items[row] = (
                self.image_items[row],
                self.image_items[row - 1],
            )

        # Refrescar tabla completa
        paths = [item.path for item in self.image_items]
        self._populate_images(paths)

    def _on_move_down(self) -> None:
        """Mueve las filas seleccionadas una posición hacia abajo."""
        selected_rows = sorted(
            [idx.row() for idx in self.table.selectionModel().selectedRows()],
            reverse=True,
        )
        if not selected_rows or selected_rows[0] >= len(self.image_items) - 1:
            return

        for row in selected_rows:
            self.image_items[row], self.image_items[row + 1] = (
                self.image_items[row + 1],
                self.image_items[row],
            )

        paths = [item.path for item in self.image_items]
        self._populate_images(paths)

    def _on_remove_selected(self) -> None:
        """Elimina de la lista las imágenes seleccionadas por el usuario."""
        selected_rows = sorted(
            [idx.row() for idx in self.table.selectionModel().selectedRows()],
            reverse=True,
        )
        if not selected_rows:
            return

        for row in selected_rows:
            if row < len(self.image_items):
                del self.image_items[row]
            self.table.removeRow(row)

        self._renumber_table()
        self._update_list_summary()

    def _on_clear_list(self) -> None:
        """Limpia completamente la lista de imágenes."""
        if not self.image_items:
            return

        self._cancel_thumbnail_loader()
        self.image_items.clear()
        self.table.setRowCount(0)
        self._update_list_summary()

    # =========================================================================
    # GESTIÓN Y UNIÓN DE PDFs
    # =========================================================================
    def _on_add_pdf_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar archivos PDF",
            str(self.destination_folder or self.source_folder or Path.home()),
            "Documentos PDF (*.pdf)",
        )
        if selected:
            self._append_pdf_paths([Path(path) for path in selected])

    def _append_pdf_paths(self, paths: list[Path]) -> None:
        existing = {path.resolve() for path in self.pdf_paths}
        for path in paths:
            if path.resolve() not in existing:
                self.pdf_paths.append(path)
                existing.add(path.resolve())
        self._refresh_pdf_table()

    def _refresh_pdf_table(self) -> None:
        self.pdf_table.setRowCount(0)
        for row, path in enumerate(self.pdf_paths):
            self.pdf_table.insertRow(row)
            number = QTableWidgetItem(f"#{row + 1}")
            number.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pdf_table.setItem(row, 0, number)
            name = QTableWidgetItem(path.name)
            self.pdf_table.setItem(row, 1, name)
            location = QTableWidgetItem(str(path.parent))
            self.pdf_table.setItem(row, 2, location)

    def _renumber_pdf_table(self) -> None:
        for row in range(self.pdf_table.rowCount()):
            item = self.pdf_table.item(row, 0)
            if item:
                item.setText(f"#{row + 1}")

    def _on_pdf_move_up(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.pdf_table.selectionModel().selectedRows()}
        )
        if not rows or rows[0] == 0:
            return
        for row in rows:
            self.pdf_paths[row - 1], self.pdf_paths[row] = (
                self.pdf_paths[row],
                self.pdf_paths[row - 1],
            )
        self._refresh_pdf_table()

    def _on_pdf_move_down(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.pdf_table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows or any(row >= len(self.pdf_paths) - 1 for row in rows):
            return
        for row in rows:
            self.pdf_paths[row], self.pdf_paths[row + 1] = (
                self.pdf_paths[row + 1],
                self.pdf_paths[row],
            )
        self._refresh_pdf_table()

    def _on_remove_pdf_files(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.pdf_table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            if 0 <= row < len(self.pdf_paths):
                del self.pdf_paths[row]
                self.pdf_table.removeRow(row)
        self._renumber_pdf_table()

    def _on_clear_pdf_files(self) -> None:
        self.pdf_paths.clear()
        self.pdf_table.setRowCount(0)

    def _on_merge_pdfs(self) -> None:
        if self.pdf_merge_worker and self.pdf_merge_worker.isRunning():
            self.pdf_merge_worker.cancel()
            self.btn_merge_pdfs.setEnabled(False)
            self.lbl_current_status.setText("Cancelando unión de PDFs...")
            return

        if not self.pdf_paths:
            QMessageBox.warning(
                self,
                "Sin archivos PDF",
                "Añade al menos dos archivos PDF para realizar la unión.",
            )
            return

        dest_raw = self.txt_dest_folder.text().strip()
        if not dest_raw:
            QMessageBox.warning(
                self,
                "Carpeta de destino vacía",
                "Indica una carpeta de destino antes de unir los PDFs.",
            )
            return

        dest_path = Path(dest_raw)
        try:
            dest_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error de carpeta",
                f"No se pudo crear la carpeta de destino:\n{exc}",
            )
            return

        pdf_name, err = valid_pdf_name(self.txt_merge_name.text())
        if err:
            QMessageBox.warning(self, "Nombre de archivo inválido", err)
            return

        allow_overwrite = self.chk_overwrite.isChecked()
        target = dest_path / pdf_name
        if target.exists() and not allow_overwrite:
            reply = QMessageBox.question(
                self,
                "Archivo existente",
                f"El archivo '{pdf_name}' ya existe.\n\n¿Deseas sobrescribirlo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                allow_overwrite = True

        self.btn_merge_pdfs.setText("CANCELAR UNIÓN")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.pdf_paths))
        self.progress_bar.setFormat("0 / 0 (0%)")
        self.lbl_current_status.setText("Iniciando unión de PDFs...")

        self.pdf_merge_worker = PdfMergeWorker(
            pdf_paths=list(self.pdf_paths),
            output_dir=dest_path,
            pdf_filename=pdf_name,
            allow_overwrite=allow_overwrite,
        )
        self.pdf_merge_worker.progress.connect(self._on_pdf_merge_progress)
        self.pdf_merge_worker.finished.connect(self._on_pdf_merge_finished)
        self.pdf_merge_worker.error.connect(self._on_pdf_merge_error)
        self.pdf_merge_worker.start()

    def _on_pdf_merge_progress(
        self, current: int, total: int, filename: str
    ) -> None:
        pct = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current} / {total} ({pct}%)")
        self.lbl_current_status.setText(f"Uniendo: {filename}")

    def _on_pdf_merge_finished(self, result: dict[str, Any]) -> None:
        self.btn_merge_pdfs.setText("UNIR PDFS")
        self.btn_merge_pdfs.setEnabled(True)

        if result.get("was_cancelled"):
            self.progress_bar.setFormat("Unión cancelada.")
            self.lbl_current_status.setText("Unión cancelada por el usuario.")
            return

        if result.get("success"):
            output_path = result["output_path"]
            self.last_generated_pdf = output_path
            self.btn_open_pdf.setEnabled(True)
            self.btn_open_folder.setEnabled(True)
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.progress_bar.setFormat("¡PDF unido con éxito!")
            self.lbl_current_status.setText(f"PDF generado: {output_path.name}")
            size_bytes = result["final_size_bytes"]
            val = float(size_bytes)
            for unit in ("B", "KB", "MB", "GB"):
                if val < 1024 or unit == "GB":
                    size_str = f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
                    break
                val /= 1024
            self.lbl_result_info.setText(
                f"<b>PDF unido exitosamente:</b> {output_path.name}<br>"
                f"• <b>Ubicación:</b> {output_path}<br>"
                f"• <b>Páginas combinadas:</b> {result['processed_pages']}<br>"
                f"• <b>Tamaño:</b> {size_str}"
            )
            self.lbl_result_info.setStyleSheet(
                "color: #15803D; font-size: 13px; line-height: 1.6;"
            )
            QMessageBox.information(
                self,
                "PDFs unidos",
                f"Se creó el archivo:\n\n{output_path}",
            )
        else:
            self.progress_bar.setFormat("No se pudo unir.")
            self.lbl_current_status.setText("No se pudo unir ningún PDF.")
            errors = result.get("errors", [])
            detail = ""
            if errors:
                detail = "\n\n" + "\n".join(
                    f"{name}: {message}" for name, message in errors[:5]
                )
            QMessageBox.critical(
                self,
                "Error al unir PDFs",
                "No se pudo leer ninguna página de los archivos seleccionados." + detail,
            )

    def _on_pdf_merge_error(self, err_msg: str) -> None:
        self.btn_merge_pdfs.setText("UNIR PDFS")
        self.btn_merge_pdfs.setEnabled(True)
        self.lbl_current_status.setText("Error durante la unión de PDFs.")
        QMessageBox.critical(
            self,
            "Error al unir PDFs",
            f"Ocurrió un error inesperado:\n\n{err_msg}",
        )

    # =========================================================================
    # DESTINO Y RUTAS
    # =========================================================================
    def _on_browse_destination(self) -> None:
        """Permite al usuario seleccionar una carpeta de destino diferente."""
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de destino para el PDF",
            str(self.destination_folder or self.source_folder or Path.home()),
        )
        if selected:
            self.destination_folder = Path(selected)
            self.txt_dest_folder.setText(str(self.destination_folder))

    def _on_same_as_source(self) -> None:
        """Restablece la carpeta de destino a la misma carpeta de origen."""
        if self.source_folder:
            self.destination_folder = self.source_folder
            self.txt_dest_folder.setText(str(self.source_folder))
        elif self.image_items:
            self.destination_folder = self.image_items[0].path.parent
            self.txt_dest_folder.setText(str(self.destination_folder))

    # =========================================================================
    # PROCESO DE CONVERSIÓN
    # =========================================================================
    def _on_start_conversion(self) -> None:
        """Valida las opciones e inicia la conversión en segundo plano."""
        if not self.image_items:
            QMessageBox.warning(
                self,
                "Sin imágenes",
                "Añade al menos una imagen antes de iniciar la conversión.",
            )
            return

        dest_raw = self.txt_dest_folder.text().strip()
        if not dest_raw:
            QMessageBox.warning(
                self,
                "Carpeta de destino vacía",
                "Indica o selecciona una carpeta de destino para el PDF.",
            )
            return

        dest_path = Path(dest_raw)
        if not dest_path.is_dir():
            try:
                dest_path.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Error de carpeta",
                    f"No se pudo crear la carpeta de destino:\n{exc}",
                )
                return

        # Validar nombre del PDF
        pdf_name, err = valid_pdf_name(self.txt_pdf_name.text())
        if err:
            QMessageBox.warning(self, "Nombre de archivo inválido", err)
            return

        # Comprobar si el archivo ya existe y advertir
        target_candidate = dest_path / pdf_name
        allow_overwrite = self.chk_overwrite.isChecked()
        if target_candidate.exists() and not allow_overwrite:
            reply = QMessageBox.question(
                self,
                "Archivo existente",
                f"El archivo '{pdf_name}' ya existe en la carpeta de destino.\n\n"
                "¿Deseas sobreescribirlo? Si seleccionas 'No', se guardará automáticamente "
                "con un nombre numerado como 'documento (1).pdf'.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                allow_overwrite = True

        # Preparar UI para la ejecución
        self.btn_convert.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_pdf.setEnabled(False)
        self.btn_open_folder.setEnabled(False)

        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.image_items))
        self.progress_bar.setFormat(f"0 / {len(self.image_items)} (0%)")
        self.lbl_current_status.setText("Iniciando motor de conversión...")

        page_size_mode = self.cmb_page_size.currentData()
        orientation_mode = self.cmb_orientation.currentData()
        margin_mm = float(self.cmb_margin.currentData())

        # Crear y arrancar trabajador en segundo plano
        self.conversion_worker = ConversionWorker(
            items=list(self.image_items),
            output_dir=dest_path,
            pdf_filename=pdf_name,
            page_size_mode=page_size_mode,
            orientation_mode=orientation_mode,
            margin_mm=margin_mm,
            allow_overwrite=allow_overwrite,
        )
        self.conversion_worker.progress.connect(self._on_conversion_progress)
        self.conversion_worker.finished.connect(self._on_conversion_finished)
        self.conversion_worker.error.connect(self._on_conversion_error)
        self.conversion_worker.start()

    def _on_conversion_progress(
        self, current: int, total: int, filename: str
    ) -> None:
        """Actualiza la barra de progreso y el estado actual."""
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current} / {total} ({pct}%)")
        self.lbl_current_status.setText(f"Procesando: {filename}")

    def _on_cancel_conversion(self) -> None:
        """Solicita la cancelación del hilo de conversión."""
        if self.conversion_worker and self.conversion_worker.isRunning():
            self.lbl_current_status.setText("Cancelando de forma segura...")
            self.btn_cancel.setEnabled(False)
            self.conversion_worker.cancel()

    def _on_conversion_finished(self, result: dict[str, Any]) -> None:
        """Gestiona el fin exitoso o la cancelación del proceso de conversión."""
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        was_cancelled = result.get("was_cancelled", False)
        if was_cancelled:
            self.progress_bar.setFormat("Conversión cancelada.")
            self.lbl_current_status.setText(
                "Proceso cancelado por el usuario. Archivo temporal eliminado."
            )
            QMessageBox.information(
                self,
                "Conversión cancelada",
                "La conversión fue cancelada. No se generaron archivos incompletos.",
            )
            return

        success = result.get("success", False)
        output_path = result.get("output_path")
        processed = result.get("processed_count", 0)
        skipped = result.get("skipped_count", 0)
        size_bytes = result.get("final_size_bytes", 0)
        errors = result.get("errors", [])

        if success and output_path:
            self.last_generated_pdf = output_path
            self.btn_open_pdf.setEnabled(True)
            self.btn_open_folder.setEnabled(True)

            val = float(size_bytes)
            for unit in ("B", "KB", "MB", "GB"):
                if val < 1024 or unit == "GB":
                    size_str = (
                        f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
                    )
                    break
                val /= 1024
            else:
                size_str = f"{val:.1f} GB"

            self.progress_bar.setValue(self.progress_bar.maximum())
            self.progress_bar.setFormat("¡Conversión completada con éxito!")
            self.lbl_current_status.setText(f"PDF generado: {output_path.name}")

            # Detalle en el panel de resultados
            summary_html = (
                f"<b>Documento creado exitosamente:</b> {output_path.name}<br>"
                f"• <b>Ubicación:</b> {output_path}<br>"
                f"• <b>Imágenes procesadas:</b> {processed}<br>"
                f"• <b>Imágenes omitidas:</b> {skipped}<br>"
                f"• <b>Tamaño del documento:</b> {size_str}"
            )
            if errors:
                err_summary = "<br>• <b>Archivos con incidencias:</b> " + ", ".join(
                    f"{name} ({msg})" for name, msg in errors[:3]
                )
                if len(errors) > 3:
                    err_summary += f" y {len(errors) - 3} más."
                summary_html += err_summary

            self.lbl_result_info.setText(summary_html)
            self.lbl_result_info.setStyleSheet(
                "color: #15803D; font-size: 13px; line-height: 1.6;"
            )

            QMessageBox.information(
                self,
                "Conversión completada",
                f"Se ha generado el documento PDF con éxito:\n\n"
                f"Archivo: {output_path.name}\n"
                f"Páginas: {processed}\n"
                f"Tamaño: {size_str}\n\n"
                "Puedes abrirlo directamente usando los botones de resultados.",
            )
        else:
            self.lbl_current_status.setText(
                "No se pudo generar el documento PDF."
            )
            QMessageBox.critical(
                self,
                "Error en la conversión",
                "No se pudo procesar ninguna de las imágenes seleccionadas. Revisa los permisos y el estado de los archivos.",
            )

    def _on_conversion_error(self, err_msg: str) -> None:
        """Gestiona excepciones no controladas emitidas por el hilo."""
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_current_status.setText("Error durante la conversión.")
        QMessageBox.critical(
            self,
            "Error en la conversión",
            f"Ocurrió un error inesperado durante el proceso:\n\n{err_msg}",
        )

    # =========================================================================
    # ACCIONES DE RESULTADOS
    # =========================================================================
    def _on_open_pdf(self) -> None:
        """Abre el archivo PDF generado en el visor predeterminado del sistema."""
        if self.last_generated_pdf and self.last_generated_pdf.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(self.last_generated_pdf))
                else:
                    import subprocess

                    cmd = (
                        ["open", str(self.last_generated_pdf)]
                        if sys.platform == "darwin"
                        else ["xdg-open", str(self.last_generated_pdf)]
                    )
                    subprocess.Popen(cmd)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "No se pudo abrir",
                    f"No se pudo abrir el visor de PDF:\n{exc}",
                )

    def _on_open_dest_folder(self) -> None:
        """Abre la carpeta de destino en el Explorador de Windows."""
        folder = (
            self.last_generated_pdf.parent
            if self.last_generated_pdf
            else self.destination_folder
        )
        if folder and folder.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(folder))
                else:
                    import subprocess

                    cmd = (
                        ["open", str(folder)]
                        if sys.platform == "darwin"
                        else ["xdg-open", str(folder)]
                    )
                    subprocess.Popen(cmd)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "No se pudo abrir",
                    f"No se pudo abrir la carpeta:\n{exc}",
                )

    def closeEvent(self, event) -> None:
        """Garantiza la detención de los hilos antes de cerrar la ventana."""
        self._cancel_thumbnail_loader()
        if self.conversion_worker and self.conversion_worker.isRunning():
            self.conversion_worker.cancel()
            self.conversion_worker.wait(1000)
        event.accept()

