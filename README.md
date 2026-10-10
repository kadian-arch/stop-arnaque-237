# Stop Arnaque 237: Cameroon Scam Reports Dataset

[![tests](https://github.com/kadian-arch/stop-arnaque-237/actions/workflows/tests.yml/badge.svg)](https://github.com/kadian-arch/stop-arnaque-237/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
[![data licence](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey)](LICENSE-DATA.md)
[![code licence](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![DOI](https://zenodo.org/badge/1389825185.svg)](https://doi.org/10.5281/zenodo.23287617)

An open dataset of real scam messages, calls and schemes reported by people in Cameroon: mobile money fraud, fake agents, fake jobs and scholarships, investment and Ponzi schemes, and more.

**Status:** v1.0 released on 10 October 2026. Still collecting reports for the next version.

**Share a scam you received (3 minutes, anonymous):** https://tally.so/r/eq4dzJ

## Why

Official alerts about scams in Cameroon are scattered across ministry pages, news sites and fact-checkers. Most of them cover fake job ads and impersonated institutions. Of the 68 alerts collected from the four main public alert feeds (StopBlaBlaCam, 237 Check, PesaCheck, MINFI), only 4 describe the everyday mobile money tricks people meet on their phones: the "wrong number" transfer, the fake promo, the call asking you to type a code. Those mostly go unrecorded. This project collects them from the people who receive them and puts them next to the public alerts, in one structured, open place.

## What's in a release

The latest release is in [`data/`](data/) (its version is in `data/VERSION`). Older versions are on the GitHub Releases page.

**Start with `messages.csv`.** Every message in the dataset, one row each, labelled `scam` or `not_scam`, with the kind of scam, language, channel and a ready-made train/test split. Messages with the same wording always fall in the same split, so a model is never tested on a copy of what it learned from.

| File | What it is |
|---|---|
| `messages` (`.csv`, `.jsonl`, `.parquet`) | the main table: every message, scam or genuine, labelled |
| `data_dictionary.csv` | what every column means and the values it can take |
| `details/reports` | the full scam reports behind the messages: how it happened, what was asked, money lost, region |
| `details/public_alerts` | scams documented by fact-checkers, institutions and news sites, or shown in public social media posts |
| `details/genuine_messages` | the genuine messages with their sender, operator and kind (money received, promo, code...) |
| `details/scam_numbers.csv` | scammer numbers (pseudonymized) and how often each appears |
| `stats.json` | counts by label, scam type, channel, region and outcome |
| `stop_arnaque_237_<version>.xlsx` | all of the above in one Excel workbook |

What makes it useful: real scam messages sit next to the genuine operator messages they imitate (MTN and Orange money alerts, promos, security tips), in English, French and Pidgin. A detector can learn to tell them apart instead of flagging every money message.

Field meanings: [DATASHEET.md](DATASHEET.md). Codes: [TAXONOMY.md](TAXONOMY.md).

## Privacy

Nothing personal is released:
- **Phone numbers** keep only the operator prefix plus a keyed code made of letters (`[PHONE:676-kqbwmx]`), so it can never be dialled. The same number gets the same code, so repeat scammers link up, but the number can't be recovered.
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
python -m pipeline huggingface v1.0 --repo-id owner/name   # dataset card + train/test files in release/hf/
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
| `pipeline/hf.py` | builds the Hugging Face copy: dataset card, train/test files, detail tables |
| `pipeline/docs.py` | generates TAXONOMY.md, so the codes and the documentation can't drift apart |
| `pipeline/export.py` | Excel workbook (with a data dictionary sheet) and Parquet copies |
| `pipeline/build.py` | merge, anonymize, link repeated messages and numbers, export, stats, review queue; the build fails if any raw number, email or private link is left in the output |
| `pipeline/harvest.py` | public sources |

Python 3.10 to 3.13, dependencies in `requirements.txt`. Raw inputs live in `raw/`, which is never committed. The tests run on every push and pull request, and weekly.

## Sources for public alerts

StopBlaBlaCam (E-SCAM), 237 Check, PesaCheck and the Ministry of Finance, plus warnings from Orange Cameroun, MTN Cameroon, MINPOSTEL, Cameroon Tribune and other Cameroonian and regional news sites (the `source` field of each alert names it). Summaries are written by this project, and each article-based alert links to its original article. Where a source quotes the scam message itself, it's kept in `example_message` (anonymized).

Some alerts come from public Facebook and Instagram posts where people shared a scam they received. For these we keep only the scam message itself and our own summary: no link, no poster name and none of the poster's own words, so nothing points back to the person who posted.

## How to cite

> Kum, D. A. (2026). *Stop Arnaque 237: Cameroon Scam Reports Dataset* (Version 1.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.23287618

To cite every version at once (it always resolves to the latest): https://doi.org/10.5281/zenodo.23287617. GitHub's "Cite this repository" button (right side of the repository page) gives the citation in BibTeX and APA.

## Licence

Data: [CC BY 4.0](LICENSE-DATA.md). Code: [MIT](LICENSE).

## Contributing

Report a scam through the form, or see [CONTRIBUTING.md](CONTRIBUTING.md) for code and documentation changes.

## Acknowledgements

Data collection: Ticha Chelsey Neh Teneng. Thanks to everyone who reported a scam or shared their messages.

## Contact

Kum Donalsien Akwo, groundtruth.cm@gmail.com
