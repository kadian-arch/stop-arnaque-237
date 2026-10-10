# Datasheet: Stop Arnaque 237

Written in the spirit of "Datasheets for Datasets" (Gebru et al.). Numbers for each release are in `release/<version>/stats.json`.

## Motivation

**Why was it created?** Scams reach people in Cameroon every day through SMS, calls, WhatsApp and social media. Public alerts exist, but they are scattered across ministry pages, news sites and fact-checkers, and they mostly cover fake job ads and impersonated institutions. The everyday scams (the "wrong number" transfer, the fake promo, the call asking for your code) rarely get written down anywhere. This dataset collects both in one structured, open place.

**Who created it?** The Stop Arnaque 237 project, led by Kum Donalsien Akwo (Buea, Cameroon). Contact: groundtruth.cm@gmail.com

**Funding:** none.

## Composition

The main file is `messages`: one row per message, labelled `scam` or `not_scam`, with scam types, language, channel, whether the text is the message itself or the person's retelling (`text_type`), where it comes from (`origin`) and a suggested 80/20 `split`. The split is keyed on the wording, so near-identical messages never land in both train and test. At most 3 messages with the same wording are included.

Behind it, in `details/`:

| File | One row is | Source |
|---|---|---|
| `reports` | one scam experience reported by a person | anonymous public form |
| `public_alerts` | one scam documented by an official body, news site or fact-checker, or shown in a public social media post | public web pages and public Facebook/Instagram posts |
| `genuine_messages` | one real message (not a scam) from an operator, bank, public service or online service | contributed by the project team and people close to it, from their own phones |
| `scam_numbers` | one scammer phone number (pseudonymized) with how often it appears | derived from the two above |

Every table comes as `.csv` (list fields joined with `|`), `.jsonl` and `.parquet`, and `data_dictionary.csv` lists every column. The ids link the tables: a row of `messages` with id `R-...` is the report with the same id in `details/reports`.

**Report fields:** channel, scam types, the message text (anonymized) and its language, text read from uploaded files, attachment types, sender type, the sender's pseudonymized number, numbers and domains in the text, call details (who the caller claimed to be, what they asked, language, how it ended), outcome, amount lost, payment rail, what the person did after, region, approximate date, and a `message_cluster` id shared by reports of the same message.

**Genuine message fields:** operator (MTN, Orange, Camtel, a bank, a public body, an online service or a partner brand), the sender name shown on the phone, line type (consumer or merchant/agent), message kind (money received or sent, agent cash-in and cash-out, loans, promos, security tips, bank alerts, codes...), the message text (anonymized), language, and how many times the same text was seen. Label: `not_scam`. When the same wording occurs more than 3 times (for example the same bundle purchase receipt with different amounts), only 3 examples are kept and `times_seen` says how often it occurred.

**Public alert fields:** source, source URL (empty for social media posts), publication date, title, a short summary written by the project, who was impersonated, who was targeted, channels, scam types, requested actions, amount requested, the scam message itself when the source quotes it (`example_message`, anonymized), pseudonymized numbers, defanged domains.

All codes are listed in [TAXONOMY.md](TAXONOMY.md).

**`multi_scam`:** the form says "tick all that apply", and many people ticked every kind of scam they have ever met rather than the one they were reporting. When 4 or more types are ticked, `multi_scam` is true: treat those labels as the person's experience, not as one incident. For training a classifier on single messages, use rows where it is false.

**Is anything missing?** Most form questions are optional, so many reports have empty fields. Many people no longer had the message; answers like "I deleted it" are left out of `message_text`. Public alerts only describe what the source article states.

**Is there sensitive data?** The raw inputs contain phone numbers, names and screenshots. None of these are released. See Anonymization.

## Collection

**Reports:** an anonymous bilingual (English/French) form on Tally, shared on WhatsApp, Facebook and LinkedIn from September 2026. Respondents must confirm they are 18 or older and agree to open publication of their anonymized report. The form never asks for names, PINs, codes, balances or ID documents.

**Public alerts:** pages from StopBlaBlaCam (E-SCAM section), 237 Check, PesaCheck and the Ministry of Finance (MINFI), 2020 to 2026, plus warnings from Orange Cameroun, MTN Cameroon, MINPOSTEL, Cameroon Tribune, Investir au Cameroun, Journal du Cameroun and other Cameroonian and regional news sites on mobile money tricks (fake credit SMS, fake agents, one-time code theft, withdrawal prompts, fake apps), online tontines, fake ticket sites, fake utility agents, WhatsApp account takeovers, loan apps, Ponzi schemes and romance scams. Only scam-related items were kept. Facts were extracted by hand. Summaries are written by the project. The article text is not republished; every article-based alert links to its source.

**Public social media posts:** Facebook and Instagram posts in which people shared a scam message they received, saved by the project team. Only the scam message itself (the scammer's words) and a summary written by the project are released. There is no link to the post, no poster name and none of the poster's own wording, since the people who posted are private individuals.

**Genuine messages:** real messages from the phones of the project team and people close to it, who agreed to share them. Names, phone numbers, account numbers, codes and IDs are removed; amounts and balances are kept.

**Time frame:** public alerts from 2008 to 2026, most from 2020 onward. Reports describe scams from any date, bucketed by the respondent (`when`).

## Anonymization

Applied by `pipeline/anonymize.py` before anything is written to a release:

- **Phone numbers** become `[PHONE:676-kqbwmx]`: the 3-digit operator prefix plus a 6-letter code from a keyed hash (HMAC-SHA256 with a private key). The code is letters only, so a pseudonym can never be mistaken for, or dialled as, someone's real number. The same number always gets the same code, so repeat scammers can be linked, but the number can't be recovered. A plain hash would not be safe: all 9-digit Cameroonian numbers can be tried in seconds.
- **Personal names** become `[NAME]`, using rules for operator message formats ("from NAME (237...)", "de NAME", "Congratulations NAME") and cues like "from", "je suis", "Mr". Contributors' own names are always masked. Any capitalized word pair that survives is flagged for manual review before release.
- **Transaction, loan and refund IDs** become `[TXN_ID]` (some loan IDs end with the borrower's number).
- **Emails** become `[EMAIL@domain]` (the domain is kept, since gmail.com vs gov.cm is a useful signal).
- **Links** are defanged (`hxxps://site[.]xyz`) so nobody clicks a live scam link.
- **Amounts and balances** are kept. Once names, numbers and account numbers are gone they point to no one, and they are part of what a real message looks like.
- **Account numbers, login codes and any other long number** become `[ACCOUNT]`, `[CODE]` or `[NUMBER]`.
- **Official operator numbers** (MTN and Orange helplines and WhatsApp lines printed in their own messages) are kept, because telling them apart from look-alikes matters.
- **Business names** of merchants are kept, but agent shop names are removed with the person, since they point to who runs them.
- **Screenshots** are never released. Their text is read with OCR, anonymized, and checked by hand.
- **Emails left for the public report** are stored separately and never released.
- **Last check:** after writing a release, the build scans every file for a raw mobile number, an email address or a private upload link, and stops if it finds one.

## Preprocessing and labels

Scam types come from what the respondent ticked. Corrections made during review are recorded privately and applied on every build, so the process is repeatable.

Uploaded files are handled by type:
- **Screenshots** are read with OCR (English and French). Long screenshots are cut into parts.
- **PDFs** give their text directly, or are OCR'd if scanned.
- **Voice notes and videos** are listened to or watched by hand.

Every transcription is checked by hand against the original before release.

Amounts typed in the form as a bare number under 1,000 are read as thousands ("50" means 50,000 FCFA), which is how people write amounts in Cameroon. `text_origin` says where `message_text` came from (`pasted`, `screenshot`, `reviewed`, or `retold` when it is the person's own account of a call or chat, often quoting the scammer), and `message_language` gives the language (`en`, `fr`, `pidgin`, `mixed`).

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
- Respondents reached through the project's own network are over-represented: most early reports come from the South West region and English-speaking groups.
- Self-reported amounts are not verified.
- Public alerts over-represent fake job ads, because that is what institutions publish about.

## Distribution and maintenance

- **Where:** GitHub (github.com/kadian-arch/stop-arnaque-237). The latest version's files are in `data/`; every version is tagged as a GitHub Release and archived on Zenodo. v1.0 DOI: https://doi.org/10.5281/zenodo.23287618. All versions: https://doi.org/10.5281/zenodo.23287617
- **Licence:** data under CC BY 4.0 (see LICENSE-DATA.md), code under MIT (see LICENSE).
- **Updates:** new versions are released as reports come in. Every version can be rebuilt from the private raw data with `python -m pipeline build --version <version>`.
- **Removal requests:** write to groundtruth.cm@gmail.com with the date you submitted and a few words from your report. The report is removed from the next version.
