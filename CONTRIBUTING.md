# Contributing

Thanks for helping. The easiest way to contribute is to **report a scam** through the form: https://tally.so/r/eq4dzJ

## Code and documentation

1. Make a branch from `main` with a short name: `lang-pidgin-words`, `fix-readme-typo`.
2. Commit small, clear changes.
3. Run the tests before pushing:
   ```bash
   pip install -r requirements.txt
   python -m pipeline test
   ```
4. Open a pull request into `main` and fill in the template. Tests run automatically; the project lead reviews and merges.

Nobody pushes straight to `main`.

## Never commit

- anything from `raw/` (reports, screenshots, contributed messages)
- `.env`, API keys, or `pipeline/.pseudonym_key`
- real phone numbers, names or screenshots in tests: use made-up values like `670000001` and `JOHN DOE TEST`

`.gitignore` blocks the private folders, but check `git status` before every commit anyway.

## Questions

Open an issue, or write to groundtruth.cm@gmail.com.
