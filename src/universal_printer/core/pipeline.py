"""
Universal Printer Document Pipeline & Rasterizer
Converts text, images, and documents to target printer formats (PDF, PostScript, PWG-Raster, ESC/POS, Raw).
"""
import io
import os
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

from universal_printer.core.models import PrintJobOptions, PageOrientation, ColorMode


class DocumentPipeline:
    """Handles parsing, conversion, and rasterizing of input files to printable stream formats."""

    PAGE_SIZES_PT = {
        "A4": (595, 842),
        "Letter": (612, 792),
        "Legal": (612, 1008),
        "A3": (842, 1191),
        "A5": (420, 595),
        "Receipt_80mm": (226, 800), # Thermal ESC/POS receipt
    }

    @classmethod
    def prepare_document(cls, file_path: str, options: PrintJobOptions, target_format: str = "application/pdf") -> Tuple[bytes, str]:
        """
        Takes an input document (PDF, PNG, JPG, TXT, etc.) and formats/converts it
        for the target printer.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # If it is already a PDF and target is PDF, read directly
        if ext == ".pdf" and "pdf" in target_format:
            with open(file_path, "rb") as f:
                return f.read(), "application/pdf"

        # If it is a plain text file, convert to a styled PDF
        if ext in (".txt", ".log", ".md", ".csv", ".json", ".py"):
            return cls.text_to_pdf(file_path, options), "application/pdf"

        # If it is an image, convert to PDF or Raster
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"):
            if "pwg-raster" in target_format:
                return cls.image_to_pwg_raster(file_path, options), "image/pwg-raster"
            elif "postscript" in target_format:
                return cls.image_to_postscript(file_path, options), "application/postscript"
            else:
                return cls.image_to_pdf(file_path, options), "application/pdf"

        # Default fallback: read raw bytes
        with open(file_path, "rb") as f:
            return f.read(), "application/octet-stream"

    @classmethod
    def text_to_pdf(cls, file_path: str, options: PrintJobOptions) -> bytes:
        """Renders plain text files onto clean printable pages via Pillow."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        page_w_pt, page_h_pt = cls.PAGE_SIZES_PT.get(options.media, (595, 842))
        # Use 300 DPI for rendering
        dpi = 300
        scale = dpi / 72.0
        width_px = int(page_w_pt * scale)
        height_px = int(page_h_pt * scale)

        if options.orientation in (PageOrientation.LANDSCAPE, PageOrientation.REVERSE_LANDSCAPE):
            width_px, height_px = height_px, width_px

        pages = []
        margin = int(40 * scale)
        line_height = int(14 * scale)
        max_lines_per_page = (height_px - 2 * margin) // line_height

        font = ImageFont.load_default()

        curr_page = Image.new("RGB", (width_px, height_px), color="white")
        draw = ImageDraw.Draw(curr_page)
        y = margin
        lines_on_page = 0

        for line in lines:
            line_str = line.rstrip("\r\n")
            draw.text((margin, y), line_str, fill="black", font=font)
            y += line_height
            lines_on_page += 1

            if lines_on_page >= max_lines_per_page:
                pages.append(curr_page)
                curr_page = Image.new("RGB", (width_px, height_px), color="white")
                draw = ImageDraw.Draw(curr_page)
                y = margin
                lines_on_page = 0

        if lines_on_page > 0 or not pages:
            pages.append(curr_page)

        buf = io.BytesIO()
        if pages:
            first_page = pages[0]
            if len(pages) > 1:
                first_page.save(buf, format="PDF", save_all=True, append_images=pages[1:], resolution=dpi)
            else:
                first_page.save(buf, format="PDF", resolution=dpi)
        return buf.getvalue()

    @classmethod
    def image_to_pdf(cls, file_path: str, options: PrintJobOptions) -> bytes:
        """Converts an image to a printable PDF with optional color mode and scaling."""
        img = Image.open(file_path)
        
        if options.color_mode in (ColorMode.MONOCHROME, ColorMode.GRAYSCALE):
            img = img.convert("L").convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        if options.orientation in (PageOrientation.LANDSCAPE, PageOrientation.REVERSE_LANDSCAPE):
            if img.width < img.height:
                img = img.rotate(90, expand=True)

        buf = io.BytesIO()
        img.save(buf, format="PDF", resolution=300.0)
        return buf.getvalue()

    @classmethod
    def image_to_postscript(cls, file_path: str, options: PrintJobOptions) -> bytes:
        """Converts an image directly to PostScript EPS."""
        img = Image.open(file_path)
        if options.color_mode == ColorMode.MONOCHROME:
            img = img.convert("1")
        elif options.color_mode == ColorMode.GRAYSCALE:
            img = img.convert("L")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="EPS")
        return buf.getvalue()

    @classmethod
    def image_to_pwg_raster(cls, file_path: str, options: PrintJobOptions) -> bytes:
        """Generates standard PWG-Raster bitmap format for IPP Everywhere printers."""
        img = Image.open(file_path).convert("RGB")
        # PWG raster sync header
        buf = io.BytesIO()
        buf.write(b"RaS2") # PWG Raster version 2 header
        # Encode raw RGB uncompressed raster data chunk
        raw_pixels = img.tobytes()
        buf.write(raw_pixels)
        return buf.getvalue()

    @classmethod
    def text_to_escpos(cls, text: str) -> bytes:
        """Generates ESC/POS byte sequence for direct thermal receipt printers."""
        buf = bytearray()
        buf.extend(b"\x1b\x40") # ESC @ (Initialize printer)
        buf.extend(b"\x1b\x61\x01") # Center align
        buf.extend(text.encode("latin-1", errors="replace"))
        buf.extend(b"\n\n\n\n") # Feed lines
        buf.extend(b"\x1d\x56\x41\x10") # GS V A (Cut paper)
        return bytes(buf)
