---
doc: spec
status: approved
---

# Marketplace Template Filler — Technical Spec

## How This Works, In Plain Language
It's a small web page that runs on your own computer (Streamlit, in Python). A team member opens it in the browser and uploads two files: the master sheet and the Amazon template. The program reads both. It learns the template's columns, which are required, and which values each dropdown allows from the template's own `Data Definitions` and `Valid Values` sheets.

Claude (the AI) proposes which master column feeds which template column. The user confirms or fixes that. For every required template column the master can't fill, the page asks one question at a time. Most answers are "same for every row" (in your filled sample, 61 of 93 filled columns are constant). Some answers depend on a master column, such as material by color, and then the page asks once per distinct value. Dropdown columns only accept the allowed values. Claude sanity-checks free-text answers.

At the end, a checker looks at every row against the rules and lists what's missing. The user downloads a copy of the original template with the data written in.

The one delicate part is saving the file. Normal Python Excel libraries rewrite the whole workbook and, in our test, dropped 3 dependent dropdowns and 21 of 22 images. So the program only opens the `.xlsm` as a zip, replaces the one sheet that holds the data (`Template`), and copies every other part unchanged.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.
1. **Upload** — the user drops the master (`.xlsx`) and template (`.xlsm`) into two boxes. → `app.py` keeps the bytes in the session. → `template_reader` and `master_reader` parse them.
2. **Map** — `mapper` first matches obvious names itself, then asks Claude about the rest. → the mapping table is shown; the user edits any pair.
3. **Ask** — `questions` builds the list of template columns that aren't covered by the mapping (required ones first). → one column per screen: value, "same for all rows" / "depends on a master column", or Skip. Dropdown columns use the allowed list. → `validator` checks each answer; Claude judges free text.
4. **Validate** — `validator` runs over all rows and shows problems per column, with a "go back and fix" link. Skipped required columns are flagged here.
5. **Download** — `xlsm_writer` writes the values into the `Template` sheet XML, copies every other zip part untouched, and offers the file.

## Stack
- **Python 3.11** (installed here).
- **Streamlit** — the web page; keeps the app in one language. https://docs.streamlit.io
- **openpyxl** — read-only parsing of the template and master. https://openpyxl.readthedocs.io
- **Python standard library `zipfile` + `lxml`** — writes the output by editing the sheet XML. https://lxml.de
- **anthropic SDK** — Claude API for mapping suggestions and judging answers. https://docs.claude.com/en/api (model: `claude-sonnet-5-5`; confirm current model id and pricing at build time).
- **pandas** — tidy handling of the 500-row master. https://pandas.pydata.org/docs
- Learner choices: Python, Streamlit, Claude API, English, run locally. The direct-XML writing approach was recommended and accepted.
- To verify early in the build: the exact XML cell format Excel expects for the written cells (inline strings vs shared strings); the Claude model id.

## Where It Runs and How Someone Tries It
- Runs locally on the user's computer, in the browser at `http://localhost:8501`. No hosting. (The learner chose local; optional deployment is not planned.)
- Needs: Python 3.11+, `pip install -r requirements.txt`, and an `ANTHROPIC_API_KEY` in a local `.env` file (git-ignored, never committed; `.env.example` shows the name).
- Start: `streamlit run app.py`.
- Demo recording: upload `sample/Master_Arias_Ring_LOT3_v2.xlsx` and `sample/RING (6).xlsm` (the blank template), confirm the mapping, answer the questions, show the validation summary, download, and open the result in Excel. Then compare to the answer key `sample/Amazon_Ring upd_ (1).xlsm`.
- Submission needs the demo video and a public GitHub repo. `sample/` is git-ignored because it holds real product data, so the repo should include a small fake sample for reviewers (see Decisions and Open Issues).
- Privacy note: product data in the master is sent to the Claude API when mapping and checking answers.

## Look and Feel
Implements `prd.md > Look and Feel`. Light theme, light background, plain Streamlit widgets, no custom branding. Progress shown as "Column 4 of 18". Labels are short English; mandatory columns are marked clearly. Usability over looks. Streamlit's built-in light theme is set in `.streamlit/config.toml`.

## Components

### Upload page
Two `st.file_uploader` boxes and a Start button, disabled until both files are present.
PRD ref: `prd.md > Upload and reading files`, `prd.md > States and Boundaries` (before upload, unusable file).
Files: `app.py`.

### Template reader
Reads the `Template` sheet: labels (row 4), attribute keys (row 5), first data row (8, taken from the settings text in `A1`). Reads `Data Definitions` for the `Required?` flag and the field description, and `Valid Values` / `Dropdown Lists` for each dropdown's allowed values. Excel's three dependent dropdowns (INDIRECT lists) can't be read as plain lists; for those columns the checker only uses the allowed values listed in `Valid Values`.
PRD ref: `prd.md > Upload and reading files`.
Files: `src/template_reader.py`.

### Master reader
Loads the master sheet into a table (about 608 rows, 36 columns in the sample).
PRD ref: `prd.md > Upload and reading files`.
Files: `src/master_reader.py`.

### Column mapper
Step one is deterministic: exact or near-exact name matches. Step two sends the leftover column names (plus a few sample values) to Claude and asks for a JSON mapping with a confidence per pair. The mapping table lets the user change any pair.
PRD ref: `prd.md > Column mapping`.
Files: `src/mapper.py`, `ui/mapping_page.py`.

### Question flow
Builds the queue: required template columns not covered by the mapping (or empty in the master), required first. Optional columns are not asked by default; an "also fill optional columns" button adds them. Each question offers three answer modes:
1. **Same for all rows** — one value (or one dropdown pick).
2. **Depends on a master column** — the user picks the master column (e.g. Color), and the page asks once per distinct value (e.g. White Gold → "White Gold").
3. **Skip.**
Claude judges free-text answers with the column's description and accepted values; invalid answers are rejected with the reason.
PRD ref: `prd.md > Asking about missing columns`.
Files: `src/questions.py`, `src/ai.py`, `ui/question_page.py`.

### Validator
Runs over all rows after the last question: required column empty, value not in the allowed list, number/format problems Claude flags. Produces a list of issues grouped by column with row counts.
PRD ref: `prd.md > Validation and QC`.
Files: `src/validator.py`, `ui/validation_page.py`.

### Template writer
Takes the original `.xlsm` bytes and the final table. Replaces only `xl/worksheets/sheet5.xml` (the `Template` sheet; found through `workbook.xml`), writing values from row 8 using inline strings and numbers, and keeps every other zip entry byte-for-byte. Output has the same file name pattern and type.
PRD ref: `prd.md > Output`.
Files: `src/xlsm_writer.py`.

## Data Model
All data lives in memory in Streamlit's session for one run (`prd.md > States and Boundaries`: nothing persists).
- `template`: list of columns (letter, label, attribute key, required flag, description, allowed values).
- `master`: a table, one row per product/variant.
- `mapping`: template column → master column (or none).
- `answers`: template column → one of {constant value, lookup {master value → answer}, skipped}.
- `result`: the final table of values to write, one row per master row.
Closing the page loses everything; downloading is the end of a run.

## File Structure
```
marketplace master/
├── app.py                  # Streamlit entry: page flow and session state
├── src/
│   ├── template_reader.py  # parse Template, Data Definitions, Valid Values
│   ├── master_reader.py    # load master sheet
│   ├── mapper.py           # name matching + Claude mapping suggestion
│   ├── questions.py        # build the question queue, store answers
│   ├── ai.py               # Claude API calls (mapping, judge answers)
│   ├── validator.py        # check all rows against the rules
│   └── xlsm_writer.py      # write values into the template zip
├── ui/                     # one file per step's screen
├── tests/                  # compares output to the answer key
├── sample/                 # real files (git-ignored)
├── samples_public/         # small fake sample for reviewers
├── .streamlit/config.toml  # light theme
├── devpost/                # Devpost learning workspace
├── requirements.txt
├── .env.example            # ANTHROPIC_API_KEY=
└── README.md               # how to run and demo
```

## External Services and Dependencies
- **Claude API** — Messages endpoint `POST https://api.anthropic.com/v1/messages` through the `anthropic` SDK. Calls: (1) mapping: send unmatched template labels/keys and master column names with sample values; expect JSON `{template_col: {master_col, confidence}}`. (2) answer check: send column description, allowed values, the user's answer; expect JSON `{ok, reason}`. Auth: `ANTHROPIC_API_KEY`. Docs: https://docs.claude.com/en/api/messages. Cost and rate limits: confirm current pricing at build time; a run is a handful of calls, not one per row.
- Everything else is a local Python library.

## Important Failure Modes
- **Claude API fails or no key** → the mapper falls back to name matching only and the user maps by hand; free-text answers are checked by the rules only, with a notice.
- **Template or master can't be read, or no `Data Definitions` / `Valid Values`** → a plain error message and upload again.
- **Output file doesn't open or loses dropdowns** → the writer test compares every zip entry except `sheet5.xml` byte-for-byte and fails the build step if anything else changed.

## What Was Simplified and Why
- **Questions only for required columns by default** instead of all ~383 — asking about every optional column would bury the user; they can opt in. (Assumption to confirm in review.)
- **Local only, no accounts, nothing saved** instead of a deployed multi-user app — matches the PoC boundary.
- **One marketplace (Amazon India ring template)** instead of a general template engine.
- **Dependent dropdowns (INDIRECT lists) checked against `Valid Values` only** instead of re-evaluating Excel's formulas — they stay intact in the output but the checker doesn't re-run them.
- **Inline strings in the written cells** instead of rewriting Excel's shared strings table — keeps the change to one file.

## Decisions and Open Issues
**Decisions (learner choices):** Python and Streamlit; Claude API; English; run locally instead of deploying; write the output by editing the `.xlsm` XML directly (recommended, accepted after the openpyxl round-trip test).
**Derived implementation details:** the session-memory data model, the file layout, `claude-sonnet-5-5` as the starting model, inline strings.
**Per-row answers (open question from the PRD):** resolved by the "depends on a master column" mode above, based on the filled sample, where only 9 of 93 filled columns vary per row. This is a recommendation, to be confirmed on review.
**Learner uncertainty:** whether a normal Excel library would keep the template intact. Clarified by testing: an openpyxl round trip lost 3 dependent dropdowns and 21 of 22 images, so the direct-XML approach was chosen. During the build, the writer's byte-for-byte test and comparing the output with the answer key are the evidence.
**Still open:**
- Confirm "required columns only by default".
- Confirm the fake sample in `samples_public/` for the public repo.
- Which columns in the template are required can vary by template version; the tool reads them from `Data Definitions` each time.
- The `.xlsm` files have no VBA macro code (no `vbaProject.bin`), so macro preservation is not an issue for these samples; the writer still copies any such part unchanged.
