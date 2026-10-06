# Stop Arnaque 237: Cameroon Scam Reports Dataset

[![tests](https://github.com/kadian-arch/stop-arnaque-237/actions/workflows/tests.yml/badge.svg)](https://github.com/kadian-arch/stop-arnaque-237/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
[![data licence](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey)](LICENSE-DATA.md)
[![code licence](https://img.shields.io/badge/code-MIT-green)](LICENSE)

An open dataset of real scam messages, calls and schemes reported by people in Cameroon: mobile money fraud, fake agents, fake jobs and scholarships, investment and Ponzi schemes, and more.

**Status:** collecting reports. First public release planned for October 2026.

**Share a scam you received (3 minutes, anonymous):** https://tally.so/r/eq4dzJ

## Why

Official alerts about scams in Cameroon are scattered across ministry pages, news sites and fact-checkers. Most of them cover fake job ads and impersonated institutions. Of the 68 alerts collected from the four main public alert feeds (StopBlaBlaCam, 237 Check, PesaCheck, MINFI), only 4 describe the everyday mobile money tricks people meet on their phones: the "wrong number" transfer, the fake promo, the call asking you to type a code. Those mostly go unrecorded. This project collects them from the people who receive them and puts them next to the public alerts, in one structured, open place.

## What's in a release

The latest release is in [`data/`](data/) (its version is in `data/VERSION`). Older versions are on the GitHub Releases page.

| File | One row is |
|---|---|
| `reports.jsonl` / `.csv` | one scam experience reported through the form |
| `public_alerts.jsonl` / `.csv` | one scam documented by an official body, news site or fact-checker, or shown in a public social media post |
| `genuine_messages.jsonl` / `.csv` | one real message (not a scam) from MTN, Orange, Camtel, a bank, a public service or an online service, so tools can learn what genuine looks like |
| `scam_numbers.csv` | one scammer number (pseudonymized) and how often it appears across reports and alerts |
| `stats.json` | counts by scam type, channel, region, outcome, amount lost, and message kind |
| `stop_arnaque_237_<version>.xlsx` | everything above in one Excel workbook, with a data dictionary sheet |
| `*.parquet` | the same tables in Parquet, for data tools and Hugging Face |

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
python -m pipeline pull                    # form submissions straight from Tally (needs TALLY_API_KEY in .env)
python -m pipeline test                    # full test suite: anonymization, form import, file types, end-to-end privacy check
python -m pipeline build --version v1.0    # raw/ -> release/v1.0/ (refused while any report awaits review)
python -m pipeline publish v1.0            # leak-scan again, then copy release/v1.0/ into data/ for committing
python -m pipeline taxonomy               # rewrite TAXONOMY.md from the code
python -m pipeline.harvest                 # re-download the public alert sources
```

| Module | Job |
|---|---|
| `pipeline/pull_tally.py` | downloads form submissions from the Tally API |
| `pipeline/ingest_form.py` | reads the Tally export: CSV (either column layout, even re-saved by Excel), XLSX, or the Google Sheets copy |
| `pipeline/attachments.py` | handles any upload: screenshots (long ones are sliced), PDFs, voice notes, videos |
| `pipeline/ocr.py` | reads screenshot text with the OCR built into Windows (English + French) |
| `pipeline/lang.py` | tags each message en / fr / pidgin / mixed |
| `pipeline/anonymize.py` | phones, names, IDs, emails, links |
| `pipeline/genuine.py` | genuine operator messages contributed by people (the "not a scam" table) |
| `pipeline/schema.py` | meaning and allowed values of every column; checks run before any release |
| `pipeline/docs.py` | generates TAXONOMY.md, so the codes and the documentation can't drift apart |
| `pipeline/export.py` | Excel workbook (with a data dictionary sheet) and Parquet copies |
| `pipeline/build.py` | merge, anonymize, link repeated messages and numbers, export, stats, review queue; the build fails if any raw number, email or private link is left in the output |
| `pipeline/harvest.py` | public sources |

Python 3.10 to 3.13, dependencies in `requirements.txt`. Raw inputs live in `raw/`, which is never committed. The tests run on every push and pull request, and weekly.

## Sources for public alerts

StopBlaBlaCam (E-SCAM), 237 Check, PesaCheck and the Ministry of Finance, plus warnings from Orange Cameroun, MTN Cameroon, MINPOSTEL, Cameroon Tribune and other Cameroonian and regional news sites (the `source` field of each alert names it). Summaries are written by this project, and each article-based alert links to its original article. Where a source quotes the scam message itself, it's kept in `example_message` (anonymized).

Some alerts come from public Facebook and Instagram posts where people shared a scam they received. For these we keep only the scam message itself and our own summary: no link, no poster name and none of the poster's own words, so nothing points back to the person who posted.

## Licence

Data: [CC BY 4.0](LICENSE-DATA.md). Code: [MIT](LICENSE).

## Contributing

Report a scam through the form, or see [CONTRIBUTING.md](CONTRIBUTING.md) for code and documentation changes.

## Acknowledgements

Data collection: Ticha Chelsey Neh Teneng. Thanks to everyone who reported a scam or shared their messages.

## Contact

Kum Donalsien Akwo, groundtruth.cm@gmail.com
