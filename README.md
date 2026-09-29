# Stop Arnaque 237: Cameroon Scam Reports Dataset

An open dataset of real scam messages, calls and schemes reported by people in Cameroon: mobile money fraud, fake agents, fake jobs and scholarships, investment and Ponzi schemes, and more.

**Status:** collecting reports. First public release planned for October 2026.

**Share a scam you received (3 minutes, anonymous):** https://tally.so/r/eq4dzJ

## Why

Official alerts about scams in Cameroon are scattered across ministry pages, news sites and fact-checkers. Most of them cover fake job ads and impersonated institutions. Of the 68 alerts collected from the four main public alert feeds (StopBlaBlaCam, 237 Check, PesaCheck, MINFI), only 4 describe the everyday mobile money tricks people meet on their phones: the "wrong number" transfer, the fake promo, the call asking you to type a code. Those mostly go unrecorded. This project collects them from the people who receive them and puts them next to the public alerts, in one structured, open place.

## What's in a release

| File | One row is |
|---|---|
| `reports.jsonl` / `.csv` | one scam experience reported through the form |
| `public_alerts.jsonl` / `.csv` | one scam campaign documented by an official body, news site or fact-checker |
| `scam_numbers.csv` | one scammer number (pseudonymized) and how often it appears across reports and alerts |
| `stats.json` | counts by scam type, channel, region, outcome |

Field meanings: [DATASHEET.md](DATASHEET.md). Codes: [TAXONOMY.md](TAXONOMY.md).

## Privacy

Nothing personal is released:
- **Phone numbers** keep only the operator prefix plus a keyed code (`[PHONE:676-3fa91c]`). The same number gets the same code, so repeat scammers link up, but the number can't be recovered.
- **Names** are removed.
- **Links** are made unclickable.
- **Screenshots** are never published.

Details in [PRIVACY.md](PRIVACY.md) and [DATASHEET.md](DATASHEET.md#anonymization).

## Pipeline

Everything from the raw form export to a release is one command, so every release can be rebuilt and checked.

```bash
python -m pipeline test                    # 40 tests: anonymization, form import, file types, end-to-end privacy check
python -m pipeline build --version v1.0    # raw/ -> release/v1.0/
python -m pipeline.harvest                 # re-download the public alert sources
```

| Module | Job |
|---|---|
| `pipeline/ingest_form.py` | reads the Tally export: CSV (either column layout, even re-saved by Excel), XLSX, or the Google Sheets copy |
| `pipeline/attachments.py` | handles any upload: screenshots (long ones are sliced), PDFs, voice notes, videos |
| `pipeline/ocr.py` | reads screenshot text with the OCR built into Windows (English + French) |
| `pipeline/lang.py` | tags each message en / fr / pidgin / mixed |
| `pipeline/anonymize.py` | phones, names, IDs, emails, links |
| `pipeline/build.py` | merge, anonymize, link repeated messages and numbers, export, stats, review queue; the build fails if any raw number, email or private link is left in the output |
| `pipeline/harvest.py` | public sources |

Python 3.10+ and `requests`, `lxml`. Raw inputs live in `raw/`, which is never committed.

## Sources for public alerts

StopBlaBlaCam (E-SCAM), 237 Check, PesaCheck and the Ministry of Finance, plus warnings from Orange Cameroun, MTN Cameroon, MINPOSTEL, Cameroon Tribune and other Cameroonian and regional news sites (the `source` field of each alert names it). Summaries are written by this project, and each alert links to its original article. Where a source quotes the scam message itself, it's kept in `example_message` (anonymized).

## Licence

Data: [CC BY 4.0](LICENSE-DATA.md). Code: [MIT](LICENSE).

## Contact

Kum Donalsien Akwo, groundtruth.cm@gmail.com
