"""Re-downloads the public sources into raw/web/ (private working copies).

python -m pipeline.harvest

- StopBlaBlaCam E-SCAM listing (4 pages, ~53 alerts)
- 237 Check WordPress API, filtered by scam keywords (most of their posts are general fact-checks)
- MINFI WordPress API, same filter
PesaCheck blocks scripted downloads; its 3 Cameroon scam articles were read in a browser.

Structured facts are then extracted by hand into raw/web/curated_public_alerts.jsonl
(summaries in our own words, source URL kept). Article text is never republished.
"""
import json
import re
import time
from pathlib import Path

import lxml.html as H
import requests

from .build import RAW

UA = {"User-Agent": "Mozilla/5.0 (StopArnaque237 open dataset; research)"}
MONTHS = {"janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "août": 8,
          "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12}
KEYWORDS = ["arnaque", "scam", "escroquerie", "fraude", "arnaqueur", "mobile money", "ponzi", "phishing",
            "faux recrutement", "fake", "hameçonnage", "usurpation", "faux compte", "orange money", "momo"]


def stopblablacam(dest: Path):
    arts = []
    for start in (0, 14, 28, 42):
        html = requests.get(f"https://www.stopblablacam.com/e-scam?start={start}", headers=UA, timeout=40).text
        (dest / f"escam_start{start}.html").write_text(html, encoding="utf-8")
        doc = H.fromstring(html)
        for item in doc.xpath('//div[contains(@class,"catItemView")]'):
            head = item.xpath('.//div[contains(@class,"catItemHeader")]//h2|.//div[contains(@class,"catItemHeader")]//h3')
            if not head:
                continue
            for s in item.xpath(".//script"):
                s.drop_tree()
            body = "\n".join(b.text_content() for b in item.xpath('.//div[contains(@class,"catItemIntroText")]|.//div[contains(@class,"catItemFullText")]'))
            m = re.search(r"Paru le\s+\w+,\s*(\d{1,2}) (\w+) (\d{4})", re.sub(r"\s+", " ", item.text_content()))
            arts.append({"source": "stopblablacam", "listing": f"https://www.stopblablacam.com/e-scam?start={start}",
                         "title": head[0].text_content().strip(),
                         "date": f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}" if m else None,
                         "body": re.sub(r"\n\s*\n+", "\n", body).strip()})
        time.sleep(2)
    return arts


def wordpress(base: str, source: str):
    seen = {}
    for q in KEYWORDS:
        try:
            posts = requests.get(f"{base}/wp-json/wp/v2/posts", headers=UA, timeout=40,
                                 params={"search": q, "per_page": 100, "_fields": "id,date,link,title,content"}).json()
        except Exception:
            continue
        for p in posts if isinstance(posts, list) else []:
            if p["id"] not in seen:
                seen[p["id"]] = {"source": source, "date": p["date"][:10], "url": p["link"],
                                 "title": H.fromstring(p["title"]["rendered"] or "x").text_content(),
                                 "body": H.fromstring(p["content"]["rendered"] or "<p></p>").text_content()}
        time.sleep(1)
    return sorted(seen.values(), key=lambda a: a["date"])


def main():
    for name, fn in [("stopblablacam", lambda d: stopblablacam(d)),
                     ("237check", lambda d: wordpress("https://237check.org", "237check")),
                     ("minfi", lambda d: wordpress("https://minfi.gov.cm", "minfi"))]:
        dest = RAW / "web" / name
        dest.mkdir(parents=True, exist_ok=True)
        arts = fn(dest)
        (dest / f"{name}_articles.json").write_text(json.dumps(arts, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}: {len(arts)} items")


if __name__ == "__main__":
    main()
