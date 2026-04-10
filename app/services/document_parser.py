from io import BytesIO
from pathlib import Path
import re
import zipfile

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_PDF_TEXT_LEN_BEFORE_OCR = 60


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _extract_from_docx(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            xml_bytes = archive.read("word/document.xml")
    except Exception as exc:
        raise ValueError("Invalid DOCX file.") from exc

    xml_text = xml_bytes.decode("utf-8", errors="ignore")
    xml_text = re.sub(r"</w:p>", "\n", xml_text)
    xml_text = re.sub(r"<[^>]+>", "", xml_text)
    text = _normalize_whitespace(xml_text)

    if not text:
        raise ValueError("No readable text found in DOCX file.")

    return text


def _extract_from_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            text = _normalize_whitespace(text)
            if text:
                return text
        except UnicodeDecodeError:
            continue

    raise ValueError("Could not decode text file.")


def _extract_from_image_ocr(file_bytes: bytes) -> str:
    try:
        import numpy as np
        from PIL import Image
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        raise ValueError(
            "OCR dependencies missing. Install: pip install rapidocr-onnxruntime pillow"
        ) from exc

    image = Image.open(BytesIO(file_bytes)).convert("RGB")
    ocr = RapidOCR()
    result, _ = ocr(np.array(image))

    if not result:
        raise ValueError("No readable text found in image.")

    lines = []
    for item in result:
        if len(item) > 1 and isinstance(item[1], str):
            lines.append(item[1])

    text = _normalize_whitespace("\n".join(lines))
    if not text:
        raise ValueError("No readable text found in image.")

    return text


def _extract_from_pdf_ocr(file_bytes: bytes) -> str:
    try:
        import numpy as np
        import pypdfium2 as pdfium
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        raise ValueError(
            "OCR dependencies missing. Install: pip install rapidocr-onnxruntime pypdfium2"
        ) from exc

    ocr = RapidOCR()
    pdf = pdfium.PdfDocument(file_bytes)
    page_text = []

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        image = page.render(scale=2.0).to_pil()
        result, _ = ocr(np.array(image))
        lines = []
        for item in result or []:
            if len(item) > 1 and isinstance(item[1], str):
                lines.append(item[1])
        if lines:
            page_text.append("\n".join(lines))

    text = _normalize_whitespace("\n\n".join(page_text))
    if not text:
        raise ValueError("No readable text found in scanned PDF.")

    return text


def _extract_from_pdf(file_bytes: bytes):
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise ValueError("PDF parsing requires 'pypdf'. Install it with: pip install pypdf") from exc

    try:
        reader = PdfReader(BytesIO(file_bytes))
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        text = _normalize_whitespace("\n".join(chunks))
    except Exception as exc:
        raise ValueError("Unable to extract text from PDF file.") from exc

    if len(text) >= MIN_PDF_TEXT_LEN_BEFORE_OCR:
        return text, "native"

    # Fallback for scanned/image-only PDFs.
    try:
        ocr_text = _extract_from_pdf_ocr(file_bytes)
        return ocr_text, "ocr"
    except ValueError:
        if text:
            return text, "native"
        raise ValueError("No readable text found in PDF file, including OCR fallback.")


async def extract_text_with_details_from_upload(file: UploadFile):
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    file_bytes = await file.read()

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large. Maximum size is 10 MB.")

    if extension == ".txt":
        return _extract_from_txt(file_bytes), {"method": "native", "extension": extension}

    if extension == ".docx":
        return _extract_from_docx(file_bytes), {"method": "native", "extension": extension}

    if extension == ".pdf":
        text, method = _extract_from_pdf(file_bytes)
        return text, {"method": method, "extension": extension}

    if extension in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        text = _extract_from_image_ocr(file_bytes)
        return text, {"method": "ocr", "extension": extension}

    if extension == ".doc":
        raise ValueError("Legacy .doc is not supported. Please upload .docx or .pdf")

    raise ValueError("Unsupported file type. Use .pdf, .docx, .txt, .png, .jpg, or .jpeg")


async def extract_text_from_upload(file: UploadFile) -> str:
    text, _ = await extract_text_with_details_from_upload(file)
    return text
