from collections.abc import Callable
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter


def merge_pdf_files(
    pdf_paths: list[Path],
    output_dir: Path,
    pdf_filename: str,
    progress_callback: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    """Une PDFs conservando las paginas originales sin rasterizarlas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / pdf_filename

    if candidate.exists() and not allow_overwrite:
        stem = candidate.stem
        suffix = candidate.suffix
        index = 1
        while candidate.exists():
            candidate = output_dir / f"{stem} ({index}){suffix}"
            index += 1

    writer = PdfWriter()
    processed_pages = 0
    errors: list[tuple[str, str]] = []

    try:
        for pdf_index, pdf_path in enumerate(pdf_paths, start=1):
            if cancel_check and cancel_check():
                return {
                    "success": False,
                    "output_path": None,
                    "processed_pages": 0,
                    "processed_files": 0,
                    "errors": errors,
                    "was_cancelled": True,
                    "final_size_bytes": 0,
                }

            if progress_callback:
                progress_callback(pdf_index, len(pdf_paths), pdf_path.name)

            try:
                reader = PdfReader(str(pdf_path), strict=False)
                if reader.is_encrypted:
                    reader.decrypt("")
                for page in reader.pages:
                    writer.add_page(page)
                    processed_pages += 1
            except Exception as exc:
                errors.append((pdf_path.name, f"{type(exc).__name__}: {exc}"))

        if processed_pages == 0:
            return {
                "success": False,
                "output_path": None,
                "processed_pages": 0,
                "processed_files": 0,
                "errors": errors,
                "was_cancelled": False,
                "final_size_bytes": 0,
            }

        with candidate.open("wb") as output_stream:
            writer.write(output_stream)

        return {
            "success": True,
            "output_path": candidate,
            "processed_pages": processed_pages,
            "processed_files": len(pdf_paths) - len(errors),
            "errors": errors,
            "was_cancelled": False,
            "final_size_bytes": candidate.stat().st_size,
        }
    except Exception:
        candidate.unlink(missing_ok=True)
        raise
