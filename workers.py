"""
Módulo de trabajadores en segundo plano (QThread) para PySide6.
Permite realizar la conversión a PDF y la carga asíncrona de miniaturas
sin bloquear la interfaz gráfica de usuario.
"""

from pathlib import Path
from typing import Any

from image_handler import ImageItem, generate_thumbnail_bytes, read_image_metadata
from pdf_generator import convert_images_to_pdf
from pdf_merger import merge_pdf_files
from PySide6.QtCore import QThread, Signal


class ConversionWorker(QThread):
    """Hilo de trabajo dedicado a la conversión de imágenes a PDF."""

    # Señales Qt
    # (índice_actual, total, nombre_archivo_actual)
    progress = Signal(int, int, str)
    # Diccionario con resumen de resultados
    finished = Signal(dict)
    # Mensaje de error crítico
    error = Signal(str)

    def __init__(
        self,
        items: list[ImageItem],
        output_dir: Path,
        pdf_filename: str,
        page_size_mode: str = "proportional",
        orientation_mode: str = "auto",
        margin_mm: float = 0.0,
        allow_overwrite: bool = False,
    ):
        super().__init__()
        self.items = items
        self.output_dir = output_dir
        self.pdf_filename = pdf_filename
        self.page_size_mode = page_size_mode
        self.orientation_mode = orientation_mode
        self.margin_mm = margin_mm
        self.allow_overwrite = allow_overwrite
        self._is_cancelled = False

    def cancel(self) -> None:
        """Solicita la cancelación segura del proceso."""
        self._is_cancelled = True

    def run(self) -> None:
        """Punto de ejecución del hilo."""
        try:

            def on_progress(current: int, total: int, filename: str) -> None:
                self.progress.emit(current, total, filename)

            def check_cancel() -> bool:
                return self._is_cancelled

            result = convert_images_to_pdf(
                items=self.items,
                output_dir=self.output_dir,
                pdf_filename=self.pdf_filename,
                page_size_mode=self.page_size_mode,
                orientation_mode=self.orientation_mode,
                margin_mm=self.margin_mm,
                progress_callback=on_progress,
                cancel_check=check_cancel,
                allow_overwrite=self.allow_overwrite,
            )
            self.finished.emit(result)

        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class PdfMergeWorker(QThread):
    """Hilo de trabajo para unir archivos PDF sin bloquear la interfaz."""

    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        pdf_paths: list[Path],
        output_dir: Path,
        pdf_filename: str,
        allow_overwrite: bool = False,
    ):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.output_dir = output_dir
        self.pdf_filename = pdf_filename
        self.allow_overwrite = allow_overwrite
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            def on_progress(current: int, total: int, filename: str) -> None:
                self.progress.emit(current, total, filename)

            result = merge_pdf_files(
                pdf_paths=self.pdf_paths,
                output_dir=self.output_dir,
                pdf_filename=self.pdf_filename,
                progress_callback=on_progress,
                cancel_check=lambda: self._is_cancelled,
                allow_overwrite=self.allow_overwrite,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class ThumbnailLoaderWorker(QThread):
    """Hilo de trabajo para cargar metadatos y miniaturas de forma asíncrona,

    evitando que la interfaz gráfica se congele al agregar muchas imágenes.
    """

    # (índice_fila, ImageItem, thumbnail_png_bytes)
    item_loaded = Signal(int, object, bytes)
    all_done = Signal()

    def __init__(self, tasks: list[tuple[int, Path]]):
        super().__init__()
        self.tasks = tasks  # lista de (row_index, path)
        self._is_cancelled = False

    def cancel(self) -> None:
        """Cancela la carga en cola si el usuario limpia la lista."""
        self._is_cancelled = True

    def run(self) -> None:
        for row_idx, path in self.tasks:
            if self._is_cancelled:
                break

            item = read_image_metadata(path)
            thumb_bytes = b""
            if item.is_valid:
                generated = generate_thumbnail_bytes(path, max_size=(80, 80))
                if generated:
                    thumb_bytes = generated

            self.item_loaded.emit(row_idx, item, thumb_bytes)

        self.all_done.emit()

