# Images to PDF — Aplicación de Escritorio Profesional

Aplicación de escritorio nativa para Windows (10 y 11) desarrollada en **Python** y **PySide6**, diseñada para convertir carpetas completas o listas personalizadas de imágenes en documentos PDF de máxima fidelidad visual, conservando la resolución original píxel a píxel y evitando pérdidas por recompresión.

---

## 🌟 Características Principales

1. **Preservación Total de Calidad (Lossless / Direct Passthrough)**:
   - **Inserción directa de JPEG**: Los archivos JPEG compatibles se incorporan directamente en el flujo del PDF (`DCTDecode`) bit a bit sin descompresión ni recompresión, preservando al 100% la calidad original y el tamaño compacto.
   - **Corrección de orientación EXIF**: Se adapta la orientación de cámara (0°, 90°, 180°, 270°) mediante transformaciones nativas de coordenadas en el lienzo del PDF, sin recodificar los píxeles.
   - **Conversión sin pérdida para otros formatos**: PNG, WEBP, BMP, TIFF, ICO y GIF se procesan sin pérdida (`FlateDecode`), respetando las dimensiones exactas.
   - **Gestión de transparencias y color**: Composición limpia de canales alfa sobre fondo blanco de alto contraste y conversión de perfiles ICC a sRGB estándar.
   - **No destructivo**: Los archivos originales nunca son modificados.

2. **Ordenamiento Natural**:
   - Ordena inteligentemente nombres como `imagen1.jpg`, `imagen2.jpg` ... `imagen10.jpg`, evitando el desorden alfabético estándar (`imagen1`, `imagen10`, `imagen2`).

3. **Interfaz Moderna y Minimalista**:
   - Desarrollada con **PySide6** (Qt6) y estilos profesionales adaptados a Windows 10 y 11.
   - Arrastrar y soltar (**Drag and Drop**): Arrastra carpetas o archivos de imagen directamente sobre la ventana.
   - Miniaturas visuales generadas de forma asíncrona para inspeccionar el documento antes de crearlo.
   - Reordenación manual: Botones para subir, bajar o eliminar elementos específicos.

4. **Configuración Avanzada del PDF**:
   - **Tamaño de página**:
     - *Proporcional a la imagen*: Cada página adopta las dimensiones físicas y proporciones exactas de la imagen.
     - *Formato A4 estándar (210 × 297 mm)*: Ajuste proporcional centrado.
   - **Orientación**: Automática (se adapta a horizontal o vertical según cada imagen), o forzada a Vertical / Horizontal.
   - **Márgenes configurables**: Sin margen (0 mm / borde a borde), 5 mm, 10 mm, 15 mm o personalizado (20 mm).
   - **Selector de destino**: Guarda el PDF en cualquier carpeta elegida o en la misma de origen.
   - **Prevención de sobreescritura accidental**: Si el archivo ya existe, pregunta al usuario o asigna un sufijo correlativo automático `(1).pdf`.

5. **Rendimiento y Segundo Plano**:
   - Conversión ejecutada en un hilo independiente (`QThread`) para mantener la interfaz siempre fluida y responsiva.
   - Barra de progreso real con porcentaje y nombre del archivo que se está procesando.
   - Botón de **Cancelación segura**: Detiene el proceso inmediatamente y elimina el archivo parcial incompleto.
   - Gestión eficiente de memoria: Las imágenes se procesan individualmente liberando memoria tras cada página.

6. **Unión de PDFs existentes**:
   - Añade varios archivos PDF y ordénalos mediante los botones de subir y bajar.
   - Puedes arrastrar PDFs directamente sobre la ventana.
   - Las páginas se incorporan sin convertirlas a imágenes, conservando el contenido y evitando recodificación y pérdida de calidad.

---

## 📁 Arquitectura Modular del Proyecto

```text
Images to Pdf/
│
├── main.py              # Punto de entrada de la aplicación
├── main_window.py       # Ventana principal, componentes Qt y eventos
├── image_handler.py     # Lectura de metadatos, EXIF, miniaturas y compatibilidad
├── pdf_generator.py     # Motor ReportLab de generación de PDF y cálculo de páginas
├── pdf_merger.py        # Unión directa de páginas PDF sin rasterizar ni recomprimir
├── workers.py           # Tareas asíncronas en segundo plano (QThread)
├── styles.py            # Hoja de estilos moderna QSS (paleta, tipografía, bordes)
├── build_exe.py         # Script de empaquetado para generar el ejecutable .exe
├── requirements.txt     # Lista de dependencias del proyecto
├── run.bat              # Lanzador rápido para Windows
└── build.bat            # Acceso directo para compilar el ejecutable
```

---

## 🚀 Requisitos e Instalación

### Requisitos del Sistema
- **Sistema Operativo**: Windows 10 o Windows 11 (64 bits).
- **Python**: Versión 3.10 o superior (solo necesario para ejecutar desde código fuente).

### Instalación de Dependencias

1. Abre una terminal (PowerShell o CMD) en la carpeta del proyecto.
2. Instala las librerías necesarias con `pip`:

```powershell
pip install -r requirements.txt
```

---

## ▶️ Ejecución de la Aplicación

Para iniciar la aplicación gráfica:

```powershell
python main.py
```

O simplemente haz doble clic en el archivo **`run.bat`**.

---

## 📦 Compilación a Ejecutable Windows (.exe)

Para distribuir la aplicación a equipos que **no tengan Python instalado**, puedes generar un ejecutable independiente (`Images_to_PDF.exe`):

1. Ejecuta el script de compilación:

```powershell
python build_exe.py
```

O haz doble clic en el archivo **`build.bat`**.

2. Al finalizar, encontrarás el ejecutable generado en:
```text
dist/Images_to_PDF.exe
```

Este archivo es totalmente autónomo y no requiere instalación previa ni dependencias externas.

---

## 📋 Formatos de Imagen Compatibles

| Formato | Extensiones | Modo de Inserción |
| :--- | :--- | :--- |
| **JPEG** | `.jpg`, `.jpeg` | **Inserción directa sin recodificar** (Lossless bit-a-bit) con rotación EXIF en canvas |
| **PNG** | `.png` | Compresión sin pérdida (`FlateDecode`), fondo blanco para transparencias |
| **WebP** | `.webp` | Conversión sin pérdida preservando resolución original |
| **BMP** | `.bmp` | Conversión sin pérdida preservando resolución original |
| **TIFF** | `.tif`, `.tiff` | Fotogramas estáticos con resolución nativa |
| **GIF** | `.gif` | Extracción del primer fotograma |
| **ICO** | `.ico` | Conversión nativa |

