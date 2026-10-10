"""Hugging Face copy of a checked release: dataset card + train/test files.

python -m pipeline huggingface v1.0   ->  release/hf/  (upload that folder's contents to the HF dataset repo)
"""
import csv
import json
import shutil
from pathlib import Path

DOI = "10.5281/zenodo.23287618"  # v1.0; update when a new version gets its own DOI
CONCEPT_DOI = "10.5281/zenodo.23287617"  # all versions, always the latest
REPO = "https://github.com/kadian-arch/stop-arnaque-237"

CARD = """---
license: cc-by-4.0
language:
- en
- fr
- wes
multilinguality: multilingual
pretty_name: "Stop Arnaque 237: Cameroon Scam Reports Dataset"
size_categories:
- n<1K
task_categories:
- text-classification
task_ids:
- multi-class-classification
tags:
- scam-detection
- fraud
- mobile-money
- sms
- cameroon
- africa
- pidgin
configs:
- config_name: messages
  default: true
  data_files:
  - split: train
    path: data/train.parquet
  - split: test
    path: data/test.parquet
- config_name: reports
  data_files: details/reports.parquet
- config_name: public_alerts
  data_files: details/public_alerts.parquet
- config_name: genuine_messages
  data_files: details/genuine_messages.parquet
- config_name: scam_numbers
  data_files: details/scam_numbers.parquet
---

# Stop Arnaque 237: Cameroon Scam Reports Dataset

Scam and genuine messages from Cameroon, labelled `scam` or `not_scam`, in English, French and Cameroonian Pidgin.
Real scam messages sit next to the genuine MTN and Orange messages they imitate (money alerts, promos, security tips),
so a detector can learn to tell them apart instead of flagging every money message.

Version {version}. Source, documentation and pipeline: {repo}. DOI of this version: https://doi.org/{doi} (all versions: https://doi.org/{concept})

## Load it

```python
from datasets import load_dataset

msgs = load_dataset("{hf_id}")                      # train and test splits
reports = load_dataset("{hf_id}", "reports")        # full scam reports behind the messages
```

## What is in it

| Config | Rows | One row is |
|---|---|---|
| `messages` (default) | {n_messages} ({n_train} train / {n_test} test) | one message, scam or genuine, labelled |
| `reports` | {n_reports} | a scam reported by a person in Cameroon: what happened, what was asked, money lost, region |
| `public_alerts` | {n_alerts} | a scam documented by fact-checkers, institutions or news sites, or shown in a public social media post |
| `genuine_messages` | {n_genuine} | a real message (not a scam) with its sender, operator and kind |
| `scam_numbers` | {n_numbers} | a scammer number (pseudonymized) and how often it appears |

`messages` columns: `id`, `text`, `label` (scam / not_scam), `scam_types`, `multi_scam`, `language` (en, fr, pidgin, mixed, unknown),
`channel`, `text_type` (verbatim, or retold by the person), `origin` (report, public_alert, social_post, contributed) and `split`.

The train/test split is keyed on the wording: near-identical messages always land in the same split, so a model is never
tested on a copy of what it learned from. At most 3 messages with the same wording are included.

Every column and allowed value: `data_dictionary.csv`. Scam type codes: TAXONOMY.md in the GitHub repository.

## Privacy

Nothing personal is released. Phone numbers become the operator prefix plus a 6-letter keyed code (`[PHONE:676-kqbwmx]`),
so repeat scammers link up but no number can be recovered or dialled. Names, account numbers, codes and transaction ids are
removed, links are made unclickable and screenshots are never published. Public social media posts keep only the scam message
and a summary written by the project. Details: DATASHEET.md and PRIVACY.md in the repository.

## Intended use

Research on scams and social engineering in Cameroon and Central Africa, training and evaluating scam detectors, awareness
material and journalism. Not for identifying or contacting anyone. A number in this dataset may be spoofed, stolen or recycled.

## Limitations

Small and growing. Early reports come mostly from the South West region and English-speaking groups. Amounts are self-reported.
Public alerts over-represent fake job adverts, because that is what institutions publish about. Some report texts are the
person's retelling rather than the original message (`text_type = retold`).

## Citation

Kum, D. A. (2026). *Stop Arnaque 237: Cameroon Scam Reports Dataset* (Version {version}) [Data set]. Zenodo. https://doi.org/{doi}

```bibtex
@dataset{{kum_2026_stop_arnaque_237,
  author    = {{Kum, Donalsien Akwo}},
  title     = {{Stop Arnaque 237: Cameroon Scam Reports Dataset}},
  year      = {{2026}},
  version   = {{{version}}},
  publisher = {{Zenodo}},
  doi       = {{{doi}}},
  url       = {{https://doi.org/{doi}}}
}}
```

Licence: data CC BY 4.0, code MIT. Contact and removal requests: groundtruth.cm@gmail.com
"""


def build_hf(root: Path, version: str, hf_id: str = "groundtruth-cm/stop-arnaque-237") -> Path:
    import pyarrow as pa
    import pyarrow.parquet as pq

    src = root / "release" / version
    if not (src / "messages.parquet").exists():
        raise RuntimeError(f"{src} has no messages.parquet: run python -m pipeline build --version {version} first")
    out = root / "release" / "hf"
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    (out / "details").mkdir()

    table = pq.read_table(src / "messages.parquet")
    splits = table.column("split").to_pylist()
    for name in ("train", "test"):
        keep = pa.array([i for i, s in enumerate(splits) if s == name], type=pa.int64())  # typed, so an empty split still works
        pq.write_table(table.take(keep), out / "data" / f"{name}.parquet")
    for f in (src / "details").glob("*.parquet"):
        shutil.copy2(f, out / "details" / f.name)
    shutil.copy2(src / "data_dictionary.csv", out / "data_dictionary.csv")

    count = lambda p: pq.read_metadata(p).num_rows
    card = CARD.format(
        version=version.lstrip("v"), repo=REPO, doi=DOI, concept=CONCEPT_DOI, hf_id=hf_id,
        n_messages=table.num_rows, n_train=splits.count("train"), n_test=splits.count("test"),
        n_reports=count(src / "details" / "reports.parquet"), n_alerts=count(src / "details" / "public_alerts.parquet"),
        n_genuine=count(src / "details" / "genuine_messages.parquet"), n_numbers=count(src / "details" / "scam_numbers.parquet"),
    )
    (out / "README.md").write_text(card, encoding="utf-8")
    return out
