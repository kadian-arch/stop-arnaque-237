"""Screenshot -> text, using Windows' built-in OCR (English + French engines).

Both engines read every image; we keep the reading with more real words.
Results are cached in raw/ocr_cache.json so re-runs are instant.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PS1 = HERE / "ocr_windows.ps1"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def _score(text: str) -> int:
    """Real words, plus extra weight for what matters most as evidence:
    USSD codes (*126*9#) and phone-like digit runs."""
    t = text or ""
    words = len(re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", t))
    codes = len(re.findall(r"[*#]\d+(?:\*\d+)*#?", t))
    digits = len(re.findall(r"\d{2,}", t))
    return words + 5 * codes + digits


def ocr_images(paths, cache_file: Path) -> dict:
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    todo = [str(Path(p).resolve()) for p in paths if str(Path(p).resolve()) not in cache]
    if todo:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n".join(todo))
            listfile = f.name
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1), "-ListFile", listfile],
            capture_output=True, text=True, encoding="utf-8", timeout=60 + 20 * len(todo),
        )
        Path(listfile).unlink(missing_ok=True)
        if proc.returncode != 0 or not proc.stdout.strip():
            raise RuntimeError(f"OCR failed: {proc.stderr.strip()[:500]}")
        raw = json.loads(proc.stdout)
        if len(todo) == 1 and not isinstance(next(iter(raw.values()), None), dict):
            raw = {todo[0]: raw}
        for path, res in raw.items():
            if "error" in res:
                cache[path] = {"text": "", "lang": None, "error": res["error"]}
                continue
            best = max(res.items(), key=lambda kv: _score(kv[1]))
            cache[path] = {"text": best[1], "lang": best[0], "all": res}
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {str(Path(p).resolve()): cache.get(str(Path(p).resolve()), {"text": ""}) for p in paths}


def images_in(folder: Path) -> list:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_EXT) if folder.exists() else []
