# Datasheet: Stop Arnaque 237

Written in the spirit of "Datasheets for Datasets" (Gebru et al.). Numbers for each release are in `release/<version>/stats.json`.

## Motivation

**Why was it created?** Scams reach people in Cameroon every day through SMS, calls, WhatsApp and social media. Public alerts exist, but they are scattered across ministry pages, news sites and fact-checkers, and they mostly cover fake job ads and impersonated institutions. The everyday scams (the "wrong number" transfer, the fake promo, the call asking for your code) rarely get written down anywhere. This dataset collects both in one structured, open place.

**Who created it?** The Stop Arnaque 237 project, led by Kum Donalsien Akwo (Buea, Cameroon). Contact: groundtruth.cm@gmail.com

**Funding:** none.

## Composition

Three files per release:

| File | One row is | Source |
|---|---|---|
| `reports` | one scam experience reported by a person | anonymous public form |
| `public_alerts` | one scam campaign documented by an official body, news site or fact-checker | public web pages |
| `scam_numbers` | one scammer phone number (pseudonymized) with how often it appears | derived from the two above |

Each comes as `.jsonl` and `.csv` (list fields joined with `|`).

**Report fields:** channel, scam types, the message text (anonymized) and its language, text read from uploaded files, attachment types, sender type, the sender's pseudonymized number, numbers and domains in the text, call details (who the caller claimed to be, what they asked, language, how it ended), outcome, amount lost, payment rail, what the person did after, region, approximate date, and a `message_cluster` id shared by reports of the same message.

**Public alert fields:** source, source URL, publication date, title, a short summary written by the project, who was impersonated, who was targeted, channels, scam types, requested actions, amount requested, the scam message itself when the source quotes it (`example_message`, anonymized), pseudonymized numbers, defanged domains.

All codes are listed in [TAXONOMY.md](TAXONOMY.md).

**Is anything missing?** Most form questions are optional, so many reports have empty fields. Public alerts only describe what the source article states.

**Is there sensitive data?** The raw inputs contain phone numbers, names and screenshots. None of these are released. See Anonymization.

## Collection

**Reports:** an anonymous bilingual (English/French) form on Tally, shared on WhatsApp and Facebook from September 2026. Respondents must confirm they are 18 or older and agree to open publication of their anonymized report. The form never asks for names, PINs, codes, balances or ID documents. The `src_channel` field records which link a report came through (group, status, dm, fb).

**Public alerts:** pages from StopBlaBlaCam (E-SCAM section), 237 Check, PesaCheck and the Ministry of Finance (MINFI), 2020 to 2026, plus warnings from Orange Cameroun, MTN Cameroon, MINPOSTEL, Cameroon Tribune, Investir au Cameroun, Journal du Cameroun and other Cameroonian and regional news sites on mobile money tricks (fake credit SMS, fake agents, one-time code theft, withdrawal prompts, fake apps), online tontines, fake ticket sites, fake utility agents, WhatsApp account takeovers, loan apps, Ponzi schemes and romance scams. Only scam-related items were kept. Facts were extracted by hand. Summaries are written by the project. The article text is not republished; every alert links to its source.

**Time frame:** public alerts from 2008 to 2026, most from 2020 onward. Reports describe scams from any date, bucketed by the respondent (`when`).

## Anonymization

Applied by `pipeline/anonymize.py` before anything is written to a release:

- **Phone numbers** become `[PHONE:676-3fa91c]`: the 3-digit operator prefix plus a code from a keyed hash (HMAC-SHA256 with a private key). The same number always gets the same code, so repeat scammers can be linked, but the number can't be recovered. A plain hash would not be safe: all 9-digit Cameroonian numbers can be tried in seconds.
- **Personal names** become `[NAME]`, using rules for operator message formats and cues like "from", "je suis", "Mr". Any capitalized word pair that survives is flagged for manual review before release.
- **Transaction IDs** become `[TXN_ID]`.
- **Emails** become `[EMAIL@domain]` (the domain is kept, since gmail.com vs gov.cm is a useful signal).
- **Links** are defanged (`hxxps://site[.]xyz`) so nobody clicks a live scam link.
- **Amounts** are kept.
- **Screenshots** are never released. Their text is read with OCR, anonymized, and checked by hand.
- **Emails left for the public report** are stored separately and never released.
- **Last check:** after writing a release, the build scans every file for a raw mobile number, an email address or a private upload link, and stops if it finds one.

## Preprocessing and labels

Scam types come from what the respondent ticked. Corrections made during review are recorded privately and applied on every build, so the process is repeatable.

Uploaded files are handled by type:
- **Screenshots** are read with OCR (English and French). Long screenshots are cut into parts.
- **PDFs** give their text directly, or are OCR'd if scanned.
- **Voice notes and videos** are listened to or watched by hand.

Every transcription is checked by hand against the original before release. `text_origin` says where `message_text` came from (`pasted`, `screenshot` or `reviewed`), and `message_language` gives the language (`en`, `fr`, `pidgin`, `mixed`).

## Uses

**Intended:**
- research on social engineering and fraud in Cameroon and Central Africa
- training and evaluating scam detection tools
- awareness material
- journalism

**Not intended:**
- identifying or contacting anyone
- re-identifying phone numbers
- presenting a pseudonymized number as proof that a specific person committed a crime

A number that appears here may be spoofed, stolen or recycled.

**Known limitations:**
- Respondents reached through the project's own network (Buea, English-speaking groups) are likely over-represented at first.
- Self-reported amounts are not verified.
- Public alerts over-represent fake job ads, because that is what institutions publish about.

## Distribution and maintenance

- **Where:** GitHub (github.com/kadian-arch/stop-arnaque-237).
- **Licence:** data under CC BY 4.0 (see LICENSE-DATA.md), code under MIT (see LICENSE).
- **Updates:** new versions are released as reports come in. Each version has its own folder under `release/`.
- **Removal requests:** write to groundtruth.cm@gmail.com with the date you submitted and a few words from your report. The report is removed from the next version.
