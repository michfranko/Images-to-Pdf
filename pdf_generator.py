"""
Módulo para la generación de documentos PDF de alta fidelidad visual.
Preserva dimensiones en píxeles, evita recompresión de JPEGs compatibles
y gestiona tamaños de página (A4 / Proporcional), orientaciones y márgenes.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from image_handler import (
    ImageItem,
    is_direct_jpeg_compatible,
    prepare_image_for_drawing,
    read_image_metadata,
)
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import reportlab.rl_config as rl_config

# Desactivar ASCII85 para almacenar flujos binarios puros más compactos
rl_config.useA85 = 0

# Factor de conversión mm a puntos tipográficos (72 pt = 1 pulgada = 25.4 mm)
MM_TO_POINTS = 72.0 / 25.4
A4_WIDTH_PT, A4_HEIGHT_PT = A4
PDF_MAX_PAGE_POINTS = 14_400.0  # Límite práctico de páginas en visores PDF


def valid_pdf_name(raw_name: str) -> tuple[str | None, str | None]:
    """Valida que el nombre de archivo sea seguro para el sistema operativo."""
    name = raw_name.strip()
    if name.lower().endswith(".pdf"):
        name = name[:-4].strip()

    if not name:
        return None, "El nombre del documento PDF no puede estar vacío."

    # Caracteres no permitidos en Windows
    invalid_chars = '<>:"/\\|?*'
    if any(char in invalid_chars or ord(char) < 32 for char in name):
        return None, "El nombre contiene caracteres no permitidos (<>:\"/\\|?*)."

    if name.endswith((".", " ")):
        return None, "El nombre no puede finalizar con un punto o espacio."

    # Nombres reservados en Windows
    stem = name.split(".")[0].upper()
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if stem in reserved:
        return None, f"'{stem}' es un nombre reservado por el sistema operativo."

    return f"{name}.pdf", None


def unique_output_path(
    folder: Path, filename: str, allow_overwrite: bool = False
) -> Path:
    """Calcula una ruta de salida no repetida para evitar sobreescrituras

    accidentales.
    """
    candidate = folder / filename
    if not candidate.exists() or allow_overwrite:
        return candidate

    stem = Path(filename).stem
    ext = Path(filename).suffix
    for i in range(1, 10_000):
        candidate = folder / f"{stem} ({i}){ext}"
        if not candidate.exists():
            return candidate

    raise FileExistsError(
        "No se encontró un nombre de salida libre tras 9999 intentos."
    )


def calculate_page_layout(
    visual_w_px: int,
    visual_h_px: int,
    dpi_x: float,
    dpi_y: float,
    page_size_mode: str = "proportional",
    orientation_mode: str = "auto",
    margin_mm: float = 0.0,
) -> tuple[float, float, float, float, float, float]:
    """Calcula las dimensiones de página y el área de trazado (x, y, w, h) en

    puntos.

    Retorna: (page_width, page_height, draw_x, draw_y, draw_width, draw_height)
    """
    margin_pt = max(0.0, float(margin_mm) * MM_TO_POINTS)
    is_landscape = visual_w_px > visual_h_px

    if page_size_mode == "a4":
        # Formato ISO A4
        if orientation_mode == "auto":
            page_w, page_h = (
                (A4_HEIGHT_PT, A4_WIDTH_PT)
                if is_landscape
                else (A4_WIDTH_PT, A4_HEIGHT_PT)
            )
        elif orientation_mode == "landscape":
            page_w, page_h = (A4_HEIGHT_PT, A4_WIDTH_PT)
        else:
            page_w, page_h = (A4_WIDTH_PT, A4_HEIGHT_PT)

        avail_w = max(1.0, page_w - 2.0 * margin_pt)
        avail_h = max(1.0, page_h - 2.0 * margin_pt)

        scale = min(avail_w / visual_w_px, avail_h / visual_h_px)
        draw_w = visual_w_px * scale
        draw_h = visual_h_px * scale

        draw_x = margin_pt + (avail_w - draw_w) / 2.0
        draw_y = margin_pt + (avail_h - draw_h) / 2.0

        return page_w, page_h, draw_x, draw_y, draw_w, draw_h

    else:
        # Formato proporcional a la imagen
        dpi_x_val = dpi_x if dpi_x and dpi_x > 0 else 150.0
        dpi_y_val = (
            dpi_y if dpi_y and dpi_y > 0 else (dpi_x_val if dpi_x_val else 150.0)
        )

        pt_w = visual_w_px * 72.0 / dpi_x_val
        pt_h = visual_h_px * 72.0 / dpi_y_val

        # Proteger frente al límite de 14.400 puntos de Acrobat
        scale = min(
            1.0,
            (PDF_MAX_PAGE_POINTS - 2.0 * margin_pt) / max(pt_w, pt_h, 1.0),
        )
        draw_w = pt_w * scale
        draw_h = pt_h * scale

        page_w = draw_w + 2.0 * margin_pt
        page_h = draw_h + 2.0 * margin_pt
        draw_x = margin_pt
        draw_y = margin_pt

        return page_w, page_h, draw_x, draw_y, draw_w, draw_h


def draw_single_image(
    pdf: canvas.Canvas,
    item: ImageItem,
    page_size_mode: str = "proportional",
    orientation_mode: str = "auto",
    margin_mm: float = 0.0,
) -> bool:
    """Traza una imagen individual en una nueva página del documento PDF.

    Prioriza inserción directa sin recompresión para JPEGs compatibles.
    Para otros formatos, utiliza métodos sin pérdida y libera memoria de
    inmediato.
    """
    path = item.path
    visual_w = item.visual_width
    visual_h = item.visual_height
    dpi_x = item.dpi_x
    dpi_y = item.dpi_y

    # Si las dimensiones no se obtuvieron previamente, intentar leerlas
    if visual_w <= 0 or visual_h <= 0:
        meta = read_image_metadata(path)
        if not meta.is_valid:
            raise ValueError(
                meta.error_message or "No se pudieron leer los metadatos."
            )
        visual_w = meta.visual_width
        visual_h = meta.visual_height
        dpi_x = meta.dpi_x
        dpi_y = meta.dpi_y
        item.exif_orientation = meta.exif_orientation

    page_w, page_h, draw_x, draw_y, draw_w, draw_h = calculate_page_layout(
        visual_w, visual_h, dpi_x, dpi_y, page_size_mode, orientation_mode, margin_mm
    )

    pdf.setPageSize((page_w, page_h))

    # Comprobar si se puede insertar el flujo JPEG directamente sin recodificar
    can_direct, orientation = is_direct_jpeg_compatible(path)

    if can_direct:
        # Inserción directa bit-a-bit del JPEG con transformación de canvas para EXIF
        if orientation == 1:
            pdf.drawImage(
                str(path), draw_x, draw_y, width=draw_w, height=draw_h
            )
        elif orientation == 3:
            # 180 grados
            pdf.saveState()
            pdf.translate(draw_x + draw_w, draw_y + draw_h)
            pdf.rotate(180)
            pdf.drawImage(str(path), 0, 0, width=draw_w, height=draw_h)
            pdf.restoreState()
        elif orientation == 6:
            # 90 grados CW (sentido horario)
            pdf.saveState()
            pdf.translate(draw_x, draw_y + draw_h)
            pdf.rotate(-90)
            pdf.drawImage(str(path), 0, 0, width=draw_h, height=draw_w)
            pdf.restoreState()
        elif orientation == 8:
            # 270 grados CW (90 CCW)
            pdf.saveState()
            pdf.translate(draw_x + draw_w, draw_y)
            pdf.rotate(90)
            pdf.drawImage(str(path), 0, 0, width=draw_h, height=draw_w)
            pdf.restoreState()
    else:
        # Formatos no-JPEG o JPEGs con orientaciones complejas:
        # Conversión sin pérdida con gestión de perfiles de color y transparencias
        prepared_img = prepare_image_for_drawing(path)
        try:
            reader = ImageReader(prepared_img)
            pdf.drawImage(reader, draw_x, draw_y, width=draw_w, height=draw_h)
        finally:
            prepared_img.close()

    pdf.showPage()
    return True


def convert_images_to_pdf(
    items: list[ImageItem],
    output_dir: Path,
    pdf_filename: str,
    page_size_mode: str = "proportional",
    orientation_mode: str = "auto",
    margin_mm: float = 0.0,
    progress_callback: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    """Genera el PDF combinando todas las imágenes válidas.

    Gestiona memoria imagen a imagen y elimina el archivo si se cancela.
    """
    output_path = unique_output_path(output_dir, pdf_filename, allow_overwrite)
    pdf_stream = None
    created = False
    processed_count = 0
    errors: list[tuple[str, str]] = []
    was_cancelled = False

    try:
        # Apertura segura del archivo de salida
        mode = "wb" if allow_overwrite else "xb"
        pdf_stream = open(output_path, mode)
        created = True

        pdf = canvas.Canvas(pdf_stream, pageCompression=1)
        total_items = len(items)

        for idx, item in enumerate(items, start=1):
            if cancel_check and cancel_check():
                was_cancelled = True
                break

            if progress_callback:
                progress_callback(idx, total_items, item.filename)

            try:
                draw_single_image(
                    pdf, item, page_size_mode, orientation_mode, margin_mm
                )
                processed_count += 1
            except Exception as exc:
                errors.append((item.filename, f"{type(exc).__name__}: {exc}"))

        if not was_cancelled and processed_count > 0:
            pdf.save()

        pdf_stream.close()
        pdf_stream = None

        if was_cancelled or processed_count == 0:
            output_path.unlink(missing_ok=True)
            created = False

        final_size = output_path.stat().st_size if created else 0

        return {
            "success": not was_cancelled and processed_count > 0,
            "output_path": output_path if created else None,
            "processed_count": processed_count,
            "skipped_count": len(errors),
            "errors": errors,
            "was_cancelled": was_cancelled,
            "final_size_bytes": final_size,
        }

    except Exception:
        if pdf_stream is not None:
            pdf_stream.close()
        if created:
            output_path.unlink(missing_ok=True)
        raise

