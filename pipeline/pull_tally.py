"""Pull every form submission straight from the Tally API into raw/tally_exports/api_latest.csv.

Needs TALLY_API_KEY in .env at the project root (never committed). The CSV has the same shape
as a Tally/Sheets export, so ingest_form reads it unchanged. File links come back freshly
signed, so screenshots download fine if the build runs soon after.
"""
import csv
import os
import re
from pathlib import Path

import requests

API = "https://api.tally.so"
FORM_ID = "eq4dzJ"


def api_key(root: Path) -> str:
    key = os.environ.get("TALLY_API_KEY")
    env = root / ".env"
    if not key and env.exists():
        m = re.search(r"^\s*TALLY_API_KEY\s*=\s*(\S+)", env.read_text(encoding="utf-8-sig"), re.M)
        key = m.group(1).strip("'\"") if m else None
    if not key:
        raise SystemExit("No TALLY_API_KEY in .env")
    return key


def fetch(key: str, form_id: str = FORM_ID):
    """-> (questions, submissions), all pages."""
    subs, page, questions = [], 1, []
    while True:
        r = requests.get(f"{API}/forms/{form_id}/submissions", params={"page": page, "limit": 100},
                         headers={"Authorization": f"Bearer {key}"}, timeout=60)
        r.raise_for_status()
        d = r.json()
        questions = d.get("questions") or questions
        subs += d.get("submissions") or []
        if not d.get("hasMore"):
            return questions, subs
        page += 1


def _cell(qtype, answer):
    if answer is None:
        return ""
    if qtype == "FILE_UPLOAD":
        return "\n".join(f.get("url", "") for f in answer if isinstance(f, dict))
    if isinstance(answer, list):
        return ", ".join(str(a) for a in answer)
    return str(answer)


def to_rows(questions, subs):
    """Flatten to one row per submission. Checkbox blocks without a title (the two consent
    boxes) get the ticked option as their column name and TRUE as the value."""
    qinfo = {q["id"]: (q.get("type"), (q.get("title") or "").strip()) for q in questions}
    headers, rows = ["Submission ID", "Respondent ID", "Submitted at"], []
    for s in subs:
        row = {"Submission ID": s["id"], "Respondent ID": s.get("respondentId", ""),
               "Submitted at": (s.get("submittedAt") or "").replace("T", " ").replace(".000Z", "")}
        for r in s.get("responses") or []:
            qtype, title = qinfo.get(r.get("questionId"), (None, ""))
            ans = r.get("answer")
            if qtype == "HIDDEN_FIELDS" and isinstance(ans, dict):
                for k, v in ans.items():
                    row[k] = v or ""
                    if k not in headers:
                        headers.append(k)
                continue
            if not title and qtype == "CHECKBOXES" and isinstance(ans, list):
                for opt in ans:
                    row[opt] = "TRUE"
                    if opt not in headers:
                        headers.append(opt)
                continue
            if title:
                row[title] = _cell(qtype, ans)
                if title not in headers:
                    headers.append(title)
        rows.append(row)
    return headers, rows


def pull(root: Path) -> Path:
    questions, subs = fetch(api_key(root))
    headers, rows = to_rows(questions, subs)
    out = root / "raw" / "tally_exports" / "api_latest.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} submissions -> {out}")
    return out
