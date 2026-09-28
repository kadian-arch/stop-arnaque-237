"""Whatever people upload in the screenshot field, turned into text we can use.

image  (png jpg jpeg webp bmp gif tif heic...) -> OCR
pdf                                            -> embedded text, or OCR of the first pages if scanned
audio / video / other                          -> kept private, flagged for manual listening/viewing
"""
from pathlib import Path

IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".heif", ".jfif"}
PDF = {".pdf"}
AUDIO = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".amr", ".3ga", ".weba"}
VIDEO = {".mp4", ".3gp", ".mov", ".avi", ".mkv", ".webm"}
CONTENT_TYPES = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif", "image/heic": ".heic",
    "image/heif": ".heif", "image/bmp": ".bmp", "application/pdf": ".pdf", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
    "audio/ogg": ".ogg", "audio/aac": ".aac", "audio/amr": ".amr", "video/mp4": ".mp4", "video/3gpp": ".3gp",
    "video/quicktime": ".mov",
}
OCR_SAFE = {".png", ".jpg", ".jpeg", ".bmp"}
MAX_SIDE = 9500  # Windows OCR refuses images above 10,000 px on a side (long scrolling screenshots)


def kind(path: Path) -> str:
    s = Path(path).suffix.lower()
    if s in IMAGE:
        return "image"
    if s in PDF:
        return "pdf"
    if s in AUDIO:
        return "audio"
    if s in VIDEO:
        return "video"
    return "other"


def ext_for(url: str, content_type: str) -> str:
    s = Path(url.split("?")[0]).suffix.lower()
    if s and len(s) <= 6:
        return s
    return CONTENT_TYPES.get((content_type or "").split(";")[0].strip().lower(), ".bin")


def ocr_ready(path: Path, work: Path) -> list:
    """Paths the Windows OCR engine can read for this file (converted/split if needed)."""
    path = Path(path)
    k = kind(path)
    if k == "pdf":
        return _pdf_pages(path, work)
    if k != "image":
        return []
    try:
        from PIL import Image
        im = Image.open(path)
    except Exception:
        return [path] if path.suffix.lower() in OCR_SAFE else [path]  # e.g. HEIC: let Windows try
    frames = []
    w, h = im.size
    if path.suffix.lower() in OCR_SAFE and max(w, h) <= MAX_SIDE:
        return [path]
    work.mkdir(parents=True, exist_ok=True)
    im = im.convert("RGB")
    if h > MAX_SIDE and h > 3 * w:
        # very long screenshot: cut into overlapping slices instead of shrinking the text
        step, top, i = MAX_SIDE - 200, 0, 0
        while top < h:
            out = work / f"{path.stem}_part{i}.png"
            im.crop((0, top, w, min(h, top + MAX_SIDE))).save(out)
            frames.append(out)
            top += step
            i += 1
        return frames
    if max(w, h) > MAX_SIDE:
        scale = MAX_SIDE / max(w, h)
        im = im.resize((int(w * scale), int(h * scale)))
    out = work / f"{path.stem}.png"
    im.save(out)
    return [out]


def pdf_text(path: Path) -> str:
    try:
        import fitz
        with fitz.open(path) as doc:
            return "\n".join(p.get_text() for p in doc).strip()
    except Exception:
        return ""


def _pdf_pages(path: Path, work: Path, max_pages=5) -> list:
    if pdf_text(path):
        return []  # has real text, no OCR needed
    try:
        import fitz
        work.mkdir(parents=True, exist_ok=True)
        out = []
        with fitz.open(path) as doc:
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                p = work / f"{path.stem}_page{i + 1}.png"
                page.get_pixmap(dpi=150).save(str(p))
                out.append(p)
        return out
    except Exception:
        return []
