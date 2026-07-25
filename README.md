# DataSanitizer

**KHIZEX Python Engineering Internship — Week 3**
Robust CSV ingestion, deduplication, and format normalization.

DataSanitizer is a command-line tool that reads a messy CSV of user
records, detects and removes duplicates, repairs broken formatting, and
writes a clean, validated CSV — routing anything it can't confidently fix
to a `rejected_rows.csv` file with a documented reason, instead of
silently dropping or mangling data.

---

## 1. Project Structure

```
DataSanitizer/
├── cli/
│   └── main.py          # Thin CLI entry point (argument parsing + pipeline wiring only)
├── schema/
│   └── models.py         # Pydantic CleanRecord model — the contract for "clean"
├── io_ops/
│   ├── reader.py          # Streaming, row-by-row CSV ingestion
│   └── writer.py          # Clean CSV + rejected_rows.csv writers
├── cleaning/
│   ├── name_cleaner.py    # Proper-case + whitespace normalization
│   ├── phone_cleaner.py   # Regex-based phone format detection & normalization
│   ├── email_cleaner.py   # Email normalization + structural validity check
│   └── date_cleaner.py    # Date format detection, ISO 8601 normalization, ambiguity flagging
├── dedupe/
│   └── dedupe.py           # Duplicate-key normalization, exact + near-dup removal, keep-rule
├── reporting/
│   ├── audit.py            # Pre-cleaning audit (columns, missing values, phone-format mix)
│   └── summary.py          # Post-run summary logging (counts + duplicate examples)
├── data/
│   ├── messy_input.csv      # Sample messy input
│   ├── cleaned_output.csv   # Generated clean output (reproducible — see below)
│   └── rejected_rows.csv    # Generated rejects file (reproducible — see below)
├── tests/
│   ├── test_cleaning.py     # Unit tests for name/phone/email/date cleaning
│   └── test_dedupe.py       # Unit tests for dedupe key, keep-rule, exact/near-dup removal
├── requirements.txt
└── README.md
```

Note: `io/` from the assignment spec is named `io_ops/` here because `io`
shadows Python's own standard-library `io` module and would break
imports throughout the project.

---

## 2. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Requires **Python 3.10+**.

---

## 3. Running the Tool

```bash
python -m cli.main \
  --input data/messy_input.csv \
  --output data/cleaned_output.csv \
  --rejects data/rejected_rows.csv \
  --log-level INFO
```

The tool refuses to run if `--output` points at the same path as
`--input` — the original input file is never overwritten.

### Running the tests

```bash
python -m unittest discover -s tests -v
```

---

## 4. The Clean-Record Schema

Defined in `schema/models.py` **before** any cleaning logic was written,
so "clean" has a precise, testable definition:

| Field         | Type          | Rule                                                              |
|---------------|---------------|--------------------------------------------------------------------|
| `full_name`   | `str`         | Non-empty after trimming; proper-cased                            |
| `email`       | `EmailStr`    | Structurally valid; domain lowercased                              |
| `phone`       | `str`         | Must match `+1XXXXXXXXXX` (10 US digits, `+1` prefix, no separators) |
| `signup_date` | `date`        | Must parse to a real calendar date; output as ISO 8601 (`YYYY-MM-DD`) |

Every output record is validated against this model before being written
to `cleaned_output.csv`. Anything that fails validation is routed to
`rejected_rows.csv` instead (see §7).

---

## 5. Pre-Cleaning Audit Findings (on `data/messy_input.csv`)

Running the tool logs an audit report before any cleaning happens. On the
provided 25-row sample file:

```
Total rows read: 25
Columns detected: full_name, email, phone, signup_date

Missing-value counts by column:
  - full_name: 0 missing
  - email: 1 missing   (Isla Fisher's row)
  - phone: 1 missing   (Henry Ford's row)
  - signup_date: 0 missing

Phone format distribution (raw, pre-cleaning):
  - dashed (415-555-1234):              10
  - parenthesized ((415) 555-1234):      3
  - dotted (415.555.1234):               3
  - with_country_code (+1 415 555 1234): 2
  - digits_only (10 digits):             2
  - other/malformed:                     4   (too few digits, stray extra dash, etc.)

Rows with non-UTF-8 characters detected: 0
```

This confirms the assignment's premise: at least four distinct phone
formats are present in the raw data, plus a handful of rows with missing
required fields.

---

## 6. Duplicate Detection

### Duplicate key: normalized email address

We key on `email.strip().lower()`, computed **after** field cleaning so
the key is always compared on normalized data. Rationale:

- Every valid clean record has exactly one email (it's a required field
  in the schema), so it's always available once a row passes cleaning.
- Names alone aren't reliable: two different people can share a name,
  and the same person can be entered with typos or reordered parts.
- Phone numbers can be shared across people (e.g. a family landline) or
  change over time, making them a weaker standalone identity signal than
  email for this dataset.

### Two dedupe passes

1. **Exact-duplicate removal** (baseline, `dedupe.remove_exact_duplicates`)
   — runs on raw rows before any cleaning, dropping rows that are
   byte-for-byte identical across every column (e.g. an accidental CSV
   re-export).
2. **Near-duplicate removal** (`dedupe.remove_duplicates`) — runs on
   already-cleaned rows, catching the realistic case: same person,
   different casing or phone formatting, which would fail an exact match
   but is clearly a duplicate once fields are normalized.

### Keep-rule (deterministic)

1. Prefer the record with the more recent `signup_date`.
2. If dates tie (or either is missing), prefer whichever record has more
   non-empty fields (the more complete record).
3. If still tied, keep whichever record was encountered first (stable,
   last-resort tie-break).

### Results on the sample file

- **Exact duplicates removed:** 0
- **Near-duplicates removed:** 2

| Example | Row A | Row B | Kept |
|---|---|---|---|
| 1 | `John Smith / John.Smith@Example.com / 2024-01-15` | `john smith / john.smith@example.com / 2024-02-20` | Row B — more recent `signup_date` |
| 2 | `Mary-Jane O'Brien / mary.obrien@example.com / 2024-03-03` | `MARY-JANE O'BRIEN / mary.obrien@example.com / 2024-03-03` | Either (identical after cleaning) — first-seen tie-break |

---

## 7. Format Repair — Regex Patterns Used

Every regex lives next to a comment explaining what it matches and why.
Summary:

**Names** (`cleaning/name_cleaner.py`)
- `\s+` — collapses runs of whitespace/tabs into a single space.
- `([\s\-'])` — splits a name into word-chunks while *keeping* the space/
  hyphen/apostrophe separators, so each chunk can be title-cased
  individually without mangling `"O'Brien"` or `"Smith-Jones"`.

**Phone numbers** (`cleaning/phone_cleaner.py`)
- `\d` — extracts every digit from the raw string regardless of which
  separator style it arrived in (dashes, dots, parens, spaces).
- Target output format: **`+1XXXXXXXXXX`** (documented explicitly). An
  11-digit number starting with a leading `1` has its country-code digit
  stripped before re-adding `+1`, so `"1-415-555-1234"` and
  `"415-555-1234"` both normalize to the same value.

**Emails** (`cleaning/email_cleaner.py`)
- `^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$` — a pragmatic
  structural check (local-part, `@`, domain labels, a 2+ letter TLD).
  Not full RFC 5322, but sufficient to catch the real malformations in
  this dataset (missing `@`, missing TLD) without false-rejecting valid
  addresses.

**Dates** (`cleaning/date_cleaner.py`)
- `^(\d{1,2})/(\d{1,2})/(\d{2,4})$` — matches slash-separated numeric
  dates so we can inspect the two numeric components: if both are ≤ 12
  and different, the format is genuinely ambiguous (could be MM/DD or
  DD/MM) and is flagged rather than guessed. If one component is > 12,
  it must be the day, so the date is parsed unambiguously.
- A list of explicit `strptime` formats (ISO, written-month with/without
  comma, `DD-Mon-YYYY`, etc.) covers the remaining unambiguous variants
  found in the sample file.

---

## 8. Before / After Examples

| # | Raw Input | Cleaned Output | Notes |
|---|---|---|---|
| 1 | `John Smith, John.Smith@Example.com, 415-555-1234, 2024-01-15` | `John Smith, john.smith@example.com, +14155551234, 2024-02-20` | Merged with its near-duplicate (see §6); kept the more recent date |
| 2 | `Jane   Doe, jane.doe@example.com, 415.555.6789, 01/15/2024` | `Jane Doe, jane.doe@example.com, +14155556789, 2024-01-15` | Whitespace collapsed; dotted phone + slash date normalized |
| 3 | `\tFrank Ocean, frank.ocean@example.com, (646) 555-0005, 2024-06-07` | `Frank Ocean, frank.ocean@example.com, +16465550005, 2024-06-07` | Leading tab stripped; parenthesized phone normalized |
| 4 | `Eva Green, eva.green@EXAMPLE.COM, 646.555.0004, "May 6, 2024"` | `Eva Green, eva.green@example.com, +16465550004, 2024-05-06` | Domain lowercased; written-month date parsed |
| 5 | `QUINN taylor, quinn.taylor@example.com, 212-555-0015, 2025-01-02` | `Quinn Taylor, quinn.taylor@example.com, +12125550015, 2025-01-02` | All-caps/mixed-case name normalized |
| 6 | `Robert  Johnson, robert.johnson@example.com, 555-1234, 2024-03-10` | — **rejected** — | Phone has only 7 digits; not confidently salvageable |
| 7 | `Bob Miller, bob.miller, 212-555-0001, 2024/04/01` | — **rejected** — | Email has no `@` symbol |
| 8 | `Carla Ruiz, carla.ruiz@example.com, 212-555-0002, 03/04/25` | — **rejected** — | Ambiguous date: could be March 4 or April 3 |
| 9 | `Isla Fisher, , 718-555-0007, 2024-09-10` | — **rejected** — | Email missing entirely |
| 10 | `Jack O'Neil, jack.oneil@example.com, 718-555-0008, 2024-13-45` | — **rejected** — | Not a valid calendar date (month 13, day 45) |

### Final counts (this run)

```
Rows read (raw input):              25
Exact duplicate rows removed:        0
Rows rejected (failed cleaning):     8
Rows cleaned successfully:          17
  of which near-duplicates removed:  2
Final rows written to clean output: 15

Reconciliation: 25 = 0 (exact dup) + 8 (rejected) + 2 (near dup) + 15 (final) ✓
```

These four numbers are always internally consistent — the summary
logger in `reporting/summary.py` prints an explicit reconciliation check
on every run.

---

## 9. Edge Cases & Judgment Calls

- **Ambiguous numeric dates** (`03/04/25`): rather than assuming a
  locale (US MM/DD vs. international DD/MM), any slash-separated date
  where *both* numeric components could be ≤ 12 and differ is flagged
  and rejected rather than silently guessed. A date is only auto-resolved
  when one component is unambiguously > 12 (so it must be the day).
- **Impossible calendar dates** (`2024-13-45`): month 13 and day 45 don't
  exist in any calendar, so this is rejected outright rather than
  clamped or reinterpreted.
- **Under/over-length phone numbers** (`555-1234`, `555`): rather than
  padding or guessing an area code, any number that doesn't reduce to
  exactly 10 digits (after optionally stripping a leading US country
  code digit) is rejected as unsalvageable.
- **Hyphenated / apostrophe names** (`Mary-Jane O'Brien`): title-cased
  chunk-by-chunk around hyphens and apostrophes so the punctuation is
  preserved and each name part is capitalized correctly, instead of a
  naive `.title()` call (which would incorrectly produce `"Mary-Jane
  O'brien"`).
- **Emails with no `@`** (`bob.miller`): flagged and rejected rather than
  guessed at (e.g. assuming a domain), since fabricating contact
  information is worse than declining to guess.
- **Near-duplicate tie-break** (identical Mary-Jane O'Brien entries after
  cleaning): when the keep-rule can't distinguish by date or
  completeness, the first-seen record is kept — arbitrary but
  deterministic and reproducible across runs.

---

## 10. Robustness Notes

- Ingestion is fully streaming (`csv.DictReader` as a generator) — the
  tool never assumes the whole file fits in memory or is pre-validated.
- Every row is processed inside a try/except in `cli/main.py`
  (`process_rows`), so an unexpected error on one row is logged and the
  row routed to rejects — it never crashes the whole run.
- The original input file is never opened in write mode; the tool
  additionally refuses to run if `--output` is set to the same path as
  `--input`.
