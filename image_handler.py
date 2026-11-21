"""
Módulo para la lectura, inspección, extracción de metadatos y preparación
de imágenes para su posterior conversión a PDF.
"""

from dataclasses import dataclass
import io
from pathlib import Path
import re
from typing import Any

from PIL import ExifTags, Image, ImageCms, ImageOps

# Formatos compatibles y su denominación visual
SUPPORTED_EXTENSIONS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".gif": "GIF (1er fotograma)",
    ".ico": "ICO",
}


@dataclass
class ImageItem:
    """Representa una imagen con sus metadatos e información de archivo."""

    path: Path
    filename: str
    extension: str
    format_label: str
    width: int
    height: int
    visual_width: int
    visual_height: int
    dpi_x: float
    dpi_y: float
    exif_orientation: int
    file_size_bytes: int
    is_valid: bool = True
    error_message: str | None = None
    thumbnail_bytes: bytes | None = None

    @property
    def file_size_display(self) -> str:
        """Formatea el tamaño del archivo en unidades legibles."""
        val = float(self.file_size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if val < 1024 or unit == "GB":
                return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
            val /= 1024
        return f"{val:.1f} GB"

    @property
    def dimensions_display(self) -> str:
        """Muestra las dimensiones visuales (respetando orientación EXIF)."""
        return f"{self.visual_width} × {self.visual_height} px"


def natural_sort_key(value: Any) -> list[Any]:
    """Genera una clave de ordenamiento natural (ej.

    'foto1, foto2... foto10').
    """
    s = str(value)
    return [
        int(chunk) if chunk.isdigit() else chunk.casefold()
        for chunk in re.split(r"(\d+)", s)
    ]


def get_exif_orientation(img: Image.Image) -> int:
    """Extrae el valor numérico de orientación EXIF (tag 0x0112 / 274).

    Valores comunes: 1 (normal), 3 (180°), 6 (90° CW), 8 (270° CW / 90° CCW).
    """
    try:
        exif = img.getexif()
        if exif:
            val = exif.get(ExifTags.Base.Orientation.value, 1)
            if isinstance(val, int) and 1 <= val <= 8:
                return val
    except Exception:
        pass
    return 1


def read_image_metadata(path: Path) -> ImageItem:
    """Lee metadatos de la imagen sin cargar su mapa de bits completo en

    memoria.
    """
    ext = path.suffix.lower()
    fmt_label = SUPPORTED_EXTENSIONS.get(ext, ext.upper().lstrip("."))
    file_size = 0
    try:
        file_size = path.stat().st_size
    except Exception:
        pass

    try:
        with Image.open(path) as img:
            if img.format == "GIF":
                img.seek(0)

            raw_w, raw_h = img.size
            orientation = get_exif_orientation(img)

            # En orientaciones 5, 6, 7, 8 las dimensiones visuales se intercambian
            if orientation in (5, 6, 7, 8):
                visual_w, visual_h = raw_h, raw_w
            else:
                visual_w, visual_h = raw_w, raw_h

            dpi = img.info.get("dpi", (150.0, 150.0))
            dpi_x = (
                float(dpi[0])
                if dpi and len(dpi) > 0 and dpi[0] and dpi[0] > 0
                else 150.0
            )
            dpi_y = (
                float(dpi[1])
                if dpi and len(dpi) > 1 and dpi[1] and dpi[1] > 0
                else dpi_x
            )

            return ImageItem(
                path=path,
                filename=path.name,
                extension=ext,
                format_label=fmt_label,
                width=raw_w,
                height=raw_h,
                visual_width=visual_w,
                visual_height=visual_h,
                dpi_x=dpi_x,
                dpi_y=dpi_y,
                exif_orientation=orientation,
                file_size_bytes=file_size,
                is_valid=True,
            )
    except Exception as exc:
        return ImageItem(
            path=path,
            filename=path.name,
            extension=ext,
            format_label=fmt_label,
            width=0,
            height=0,
            visual_width=0,
            visual_height=0,
            dpi_x=150.0,
            dpi_y=150.0,
            exif_orientation=1,
            file_size_bytes=file_size,
            is_valid=False,
            error_message=f"{type(exc).__name__}: {exc}",
        )


def generate_thumbnail_bytes(
    path: Path, max_size: tuple[int, int] = (80, 80)
) -> bytes | None:
    """Genera una miniatura en formato PNG optimizado para la interfaz gráfica.

    Usa fondo blanco para transparencias y respeta la orientación EXIF.
    """
    try:
        with Image.open(path) as source:
            if source.format == "GIF":
                source.seek(0)

            # Corregir orientación EXIF para la miniatura
            oriented = ImageOps.exif_transpose(source)
            oriented.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Si tiene transparencia o paleta, componer sobre blanco
            if "A" in oriented.getbands() or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                canvas_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                canvas_bg.paste(rgba, (0, 0), rgba)
                final_thumb = canvas_bg.convert("RGB")
            else:
                final_thumb = oriented.convert("RGB")

            buffer = io.BytesIO()
            final_thumb.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except Exception:
        return None


def is_direct_jpeg_compatible(path: Path) -> tuple[bool, int]:
    """Determina si un archivo JPEG puede ser insertado directamente en el PDF

    sin recompresión, y devuelve su orientación EXIF (1, 3, 6, 8).
    """
    ext = path.suffix.lower()
    if ext not in (".jpg", ".jpeg"):
        return False, 1

    try:
        with Image.open(path) as img:
            if img.format != "JPEG":
                return False, 1
            if img.mode not in ("RGB", "L", "CMYK"):
                return False, 1
            orientation = get_exif_orientation(img)
            # Orientaciones estándar 1, 3, 6, 8 se adaptan mediante transformaciones de canvas
            if orientation in (1, 3, 6, 8):
                return True, orientation
            return False, orientation
    except Exception:
        return False, 1


def prepare_image_for_drawing(path: Path) -> Image.Image:
    """Prepara una imagen para conversión sin pérdida (para formatos no-JPEG o

    cuando se requiere procesamiento):
    1. Corrige orientación EXIF.
    2. Aplica gestión de perfiles de color (convierte a sRGB).
    3. Gestiona transparencias componiendo limpiamente sobre fondo blanco.
    4. Garantiza dimensiones nativas en píxeles.
    """
    with Image.open(path) as source:
        if source.format == "GIF":
            source.seek(0)

        # 1. Corregir orientación EXIF de forma nativa
        oriented = ImageOps.exif_transpose(source)

        # 2. Gestión de perfiles de color ICC
        icc_data = source.info.get("icc_profile")
        if icc_data:
            try:
                src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_data))
                srgb_profile = ImageCms.createProfile("sRGB")
                oriented = ImageCms.profileToProfile(
                    oriented, src_profile, srgb_profile, outputMode=oriented.mode
                )
            except Exception:
                pass  # Conservar modo actual si el perfil no es convertible

        # 3. Gestión de transparencias sobre fondo blanco
        if "A" in oriented.getbands() or "transparency" in oriented.info:
            rgba = oriented.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            alpha_mask = rgba.getchannel("A")
            bg.paste(rgba, (0, 0), mask=alpha_mask)
            rgba.close()
            return bg
        elif oriented.mode != "RGB":
            return oriented.convert("RGB")
        else:
            return oriented.copy()


def find_images_in_folder(
    folder: Path, recursive: bool = False, natural_order: bool = True
) -> list[Path]:
    """Busca archivos de imagen en una carpeta especificada con orden natural."""
    if not folder.is_dir():
        return []

    pattern = "**/*" if recursive else "*"
    found = [
        item
        for item in folder.glob(pattern)
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if natural_order:
        found.sort(key=lambda p: natural_sort_key(p.name))
    else:
        found.sort(key=lambda p: (p.name.casefold(), p.name))

    return found

