# Marketplace Template Filler

Fills a marketplace's upload template (Amazon India jewelry ring template first) from your master product
sheet. The tool maps columns for you, asks one question per column the master can't fill, checks the result
against the template's rules, and gives back the **same `.xlsm` file** with the data filled in.

Built for a listing team who fill these templates by hand for hundreds of products and variants.

## How it works

Five short steps, with a step bar at the top: **Upload, Prepare, Answers, Check, AI review & download**.

1. **Upload** the master sheet (`.xlsx`) and the Amazon template (`.xlsm`).
2. **Rules** — built-in listing rules (`rules/amazon_in_jewellery.json`, editable) fill what your team
   already knows: parent/child rows, product type, metal and units, fixed values, translated values.
   You can switch them off on the page.
3. **Map** — columns with matching names are paired automatically; *Ask Claude to map the rest* proposes more
   pairs. You confirm or change any pair.
4. **Answer sheet** — every remaining column on one screen, grouped by template section and pre-filled
   from your last answers, *Let Claude propose answers* and the template's own suggestions. Fix what is
   wrong, leave a row blank to skip it, press *Apply all answers*. Answers that differ per product (e.g.
   Material by Color) have their own box. Answers are remembered on this computer for the next run
   (`answers/`, git-ignored). A one-at-a-time mode is also available.
5. **Validation** — what is still empty or doubtful, with a *Fix this* button for each item.
6. **AI review** (optional) — Claude reads the template's own rules and your finished data and lists what looks
   wrong, ranked, each marked *template rule* or *general knowledge - verify*. It is advice, not legal advice.
7. **Download** the filled template. Only the `Template` sheet is edited; dropdown rules, images, hidden
   sheets and everything else in the file are copied across untouched.

## Run it

You need Python 3.9 or newer.

```bash
python -m pip install -r requirements.txt     # use the same Python that runs streamlit
cp .env.example .env     # (Windows: copy .env.example .env) then put your key in .env
python -m streamlit run app.py                # opens http://localhost:8501
```

The Claude API key is optional. Without it, name matching still works and answers are checked against the
template rules only. `.env` is git-ignored; never commit a key.

**Privacy:** when AI mapping or the answer check is used, column names, a few sample values and your typed
answers are sent to the Claude API. Nothing else leaves your computer.

## Try it

- `samples_public/demo_master.xlsx` is a small fake master (4 rows, no real products). Regenerate it with
  `python samples_public/make_sample_master.py`.
- Download a fresh **Amazon "Ring" template (.xlsm)** from Seller Central and upload it with the demo
  master. The template is not included in this repository because its header contains seller account
  identifiers.

A one-minute demo: upload both files → *Read files* → *Ask Claude to map the rest* → answer a few questions →
look at the validation summary → *Download filled template* → open it in Excel.

## Tests

```bash
python -m pytest tests -q
```

Tests that need real files skip themselves when a local `sample/` folder (git-ignored) is missing. With the
samples present they check, among other things, that only the `Template` sheet changes, that all dropdown
rules and images survive, and that the output matches a hand-filled Amazon file wherever the master has the
data.

## Limits (proof of concept)

- Amazon India ring template only; one master and one template per run (about 500 rows).
- Dropdown lists are read from the template's `Valid Values` sheet. They are approximate, so mismatches are
  shown as "check these" rather than blocking errors. Excel's dependent (formula-driven) dropdowns are kept
  intact in the output but are not re-evaluated.
- Nothing is saved between runs.

## License

MIT, see [LICENSE](LICENSE).
