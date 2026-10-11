---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [x] **1. You can upload both files and see what the tool understood**
  Becomes usable: A running Streamlit page with two upload boxes. After upload it shows the master (rows, columns) and the template's structure: number of columns, how many are required, how many have dropdown lists.
  Why now: Proves the whole reading path (the template's `Data Definitions` / `Valid Values` rules, row 4/5/8 layout) before anything depends on it, and includes scaffold, dependencies and config.
  PRD ref: `prd.md > Upload and reading files`, `prd.md > States and Boundaries` (before upload, unusable file)
  Spec ref: `spec.md > Upload page`, `spec.md > Template reader`, `spec.md > Master reader`, `spec.md > File Structure`
  Build: Create the file structure, `requirements.txt`, `.env.example`, `.streamlit/config.toml` (light theme), `src/template_reader.py`, `src/master_reader.py`, and `app.py` with the two uploaders and the summary. Start button stays disabled until both files are present; unreadable files show a plain error.
  Verify (mechanical): Run a script that reads `sample/RING (6).xlsm` and `sample/Master_Arias_Ring_LOT3_v2.xlsx` and prints 383 template columns, the required count, and 608 master rows; start `streamlit run app.py` and confirm it serves without errors.
  Learner check: Open the app, upload your master and the blank Amazon template, and say whether the counts and the list of required columns match what you expect.
  Commit: `Add upload page and template/master readers`

- [x] **2. You can download a template with the master's data written in**
  Becomes usable: Pressing a button downloads the same `.xlsm` with the master's matching columns written into the Template sheet from row 8, everything else in the file untouched.
  Why now: This is the riskiest piece in the spec (saving without losing dropdowns and images). Proving it with simple name-matched columns now means every later slice can rely on it.
  PRD ref: `prd.md > Output`
  Spec ref: `spec.md > Template writer`, `spec.md > Why the writer edits the file directly` (Stack and Decisions)
  Build: `src/xlsm_writer.py` replaces only the `Template` sheet XML (found through `workbook.xml`), writes strings and numbers as inline values from the data row, and copies every other zip entry byte-for-byte. Add a basic name-matching function in `src/mapper.py` and a Download button for the name-matched result.
  Verify (mechanical): A test confirms every zip entry except the Template sheet is byte-identical to the input, the 3 dependent dropdown definitions and 22 images are still present, 608 rows are written, and the file reopens with openpyxl.
  Learner check: Download the file, open it in Excel, and confirm it opens without a repair message, the dropdown arrows still work, and the first rows contain your master's data.
  Commit: `Add direct-XML template writer and download`

- [x] **3. The AI proposes a mapping and you can correct it**
  Becomes usable: After upload, a mapping table shows each template column's proposed master column (name matching first, Claude for the rest); you can change any pair, and the download uses your mapping.
  Why now: First half of the kernel (the AI-assisted mapping) and the first place the Claude API is used, so key handling and fallback get tested early.
  PRD ref: `prd.md > Column mapping`
  Spec ref: `spec.md > Column mapper`, `spec.md > External Services and Dependencies`, `spec.md > Important Failure Modes`
  Build: `src/ai.py` (Claude call, JSON reply), the Claude step in `src/mapper.py`, `ui/mapping_page.py` with an editable table. If there is no API key or the call fails, show a notice and keep name matching only.
  Verify (mechanical): With the key set, run the mapper on the sample files and confirm it returns a mapping with confidences, and that the master's Brand, Color, and image URL columns map to the right template columns; with the key removed, confirm the fallback message and name-only mapping.
  Learner check: Upload both files, read the proposed mapping, change one wrong pair, and download; say whether the proposed pairs make sense for your jewelry columns.
  Commit: `Add Claude-assisted column mapping with editable table`

- [x] **4. The tool asks you about the columns the master can't fill**
  Becomes usable: One required, unmapped column per screen with progress, three answer modes (same for all rows, depends on a master column, skip), dropdown columns limited to the allowed values, and an optional "also ask optional columns" button. Your answers fill the rows.
  Why now: This is the unique kernel (the column-by-column interview). It comes right after mapping so the rest of the build can polish a working core.
  PRD ref: `prd.md > Asking about missing columns`, `prd.md > The Core Journey` (step 4)
  Spec ref: `spec.md > Question flow`, `spec.md > Data Model`
  Build: `src/questions.py` builds the queue from the template's required flags and the mapping; `ui/question_page.py` shows one question at a time; answers are stored in session state and merged into the result table before download.
  Verify (mechanical): A test builds the queue for the sample files and confirms every required, unmapped column appears; applying a "same for all" answer, a dropdown answer and a "depends on Color" lookup fills the right rows; a value outside the dropdown is rejected.
  Learner check: Go through the questions for your ring template, answer a few, skip one required column, and say whether the questions feel clear and in a sensible order.
  Commit: `Add column-by-column question flow`

- [x] **5. Validation tells you what's still wrong before you download**
  Becomes usable: After the questions, a validation page lists remaining problems by column (empty required columns, values outside the allowed list, odd formats) with a link back to fix each; Claude also judges free-text answers.
  Why now: Completes the kernel promise (every required column filled and valid) on top of working mapping and questions.
  PRD ref: `prd.md > Validation and QC`, `prd.md > States and Boundaries` (skipped mandatory column, invalid answer)
  Spec ref: `spec.md > Validator`, `spec.md > Important Failure Modes`
  Build: `src/validator.py` checks all rows against required flags and allowed values; `ui/validation_page.py` shows the summary and go-back links; add the Claude answer check in `src/ai.py` with the rules-only fallback.
  Verify (mechanical): A test runs the validator on a result with a skipped required column and a bad dropdown value and confirms both are reported with row counts; a complete result reports no problems; with the key removed, the fallback notice appears.
  Learner check: Skip a required column on purpose, reach validation, confirm it is flagged and you can go back to fix it, then download once it's clean.
  Commit: `Add validation summary and answer checking`

- [x] **6. The output matches your hand-filled file and anyone can try it**
  Becomes usable: A comparison test of the tool's output against `Amazon_Ring upd_ (1).xlsm`, plus a README with the exact run steps and a small fake master for reviewers.
  Why now: The final proof of the "working" criterion in scope, and the demo-readiness material for submission.
  PRD ref: `prd.md > What We're Building`, `prd.md > Output`
  Spec ref: `spec.md > Where It Runs and How Someone Tries It`, `spec.md > File Structure`
  Build: `tests/` compare the produced values with the answer key for the mapped and constant columns; `samples_public/` fake master (no real product data or account identifiers); `README.md` with install, key setup, start command, and demo steps.
  Verify (mechanical): Run the comparison test and report the share of cells that match the answer key and which differ; run the README steps from a clean shell and confirm the app starts.
  Learner check: Follow the README yourself from scratch and say whether the demo flow is something you could record in a minute.
  Commit: `Add answer-key comparison, fake sample and README`

- [x] **7. Built-in listing rules fill what your team already knows**
  Becomes usable: A "Built-in listing rules" step that fills parent/child markers, Product Type, browse node, metal fields, units, translated values and fixed values from `rules/amazon_in_jewellery.json`, so the questions only cover what is left.
  Why now: Added after the learner shared the rule logic of an earlier tool and chose to focus on rules; it cuts the question list and uses the learner's own business knowledge.
  PRD ref: `prd.md > Built-in listing rules`
  Spec ref: `spec.md > Rules engine`
  Build: `src/rules.py`, `rules/amazon_in_jewellery.json`, `ui/rules_page.py`; rules override raw master values, answers fill gaps; rule-covered columns leave the question queue; validator knows child-only columns; "Skip all conditionally required" button.
  Verify (mechanical): `tests/test_rules.py` compares the rule output with the hand-filled file (95.3% of 31,008 cells, differences only in images and one unit cell), checks parent/child structure, inheritance, dropdown fit, and that the question list shrinks.
  Learner check: Upload your files, read the rules summary, then go through the questions and confirm that the columns the rules filled (Product Type, Metal Type, Certificate Type, ...) are no longer asked and look right in the downloaded file.
  Commit: `Add built-in listing rules layer`

- [x] **8. Answer the remaining columns on one pre-filled sheet**
  Becomes usable: One "Answer sheet" with every remaining column in tabs, pre-filled from saved answers, Claude proposals (0.8+ confidence) and template suggestions, applied with one button and remembered for the next run.
  Why now: Added after the learner found one-question-at-a-time too slow; it keeps the interview's purpose (fill what is missing) at a fraction of the clicks.
  PRD ref: `prd.md > Answer sheet`
  Spec ref: `spec.md > Answer sheet`
  Build: `ui/answer_sheet.py`, `src/answer_store.py`, `propose_answers` in `src/ai.py`; the app offers "Answer sheet" (default) or "One at a time".
  Verify (mechanical): `tests/test_answer_sheet.py` and `tests/test_answer_sheet_logic.py` check the sheet's rows and pre-fill, apply (blank = skip), saving and reloading answers, Claude proposals (stand-in client) filling blank rows only, and the no-key message; a live run scored Claude's proposals against the hand-filled file.
  Learner check: Upload your files, press "Let Claude propose answers", fix what is wrong, press "Apply all answers", then upload the same files again and confirm your answers come back pre-filled.
  Commit: `Add answer sheet with Claude proposals and saved answers`

- [x] **9. A cleaner four-step site that is easy to handle**
  Becomes usable: A header, clickable step bar with progress, summary chips and one short screen per step (Upload, Prepare, Answers, Check & download) with Back / Continue buttons and larger light-coloured controls.
  Why now: Added after the learner asked for the site to look better and be easier to handle.
  PRD ref: `prd.md > Four-step layout`
  Spec ref: `spec.md > Page frame and steps`
  Build: `ui/layout.py`, `ui/upload_page.py`, `app.py`; rules page split into compute and display; "Fix this" returns to the Answers step.
  Verify (mechanical): `tests/test_steps.py` walks every step with the buttons and the step bar; the older screen tests open on the right step; a real-browser screenshot of each step was reviewed.
  Learner check: Run the app, upload your files, click through the four steps, and say whether each screen is clear and quick to use.
  Commit: `Redesign as a four-step site`

- [x] **10. A last AI review step checks the file against the template's rules**
  Becomes usable: A fifth step, "AI review & download", where Claude reads the template's own rule text and the finished data and lists ranked findings with their source (template rule or general knowledge), plus Fix this and download.
  Why now: Added after the learner asked for AI validation against the file's rules and regulations as the last step.
  PRD ref: `prd.md > AI review (last step)`
  Spec ref: `spec.md > AI review`
  Build: `src/review.py`, `ui/review_page.py`, instructions read in `src/template_reader.py`, five-step flow in `app.py` and `ui/layout.py`.
  Verify (mechanical): `tests/test_review.py` checks the context, parsing, ranking, truncated replies, failure messages and the screen (stand-in client); a live run reviewed the hand-filled file and our own output.
  Learner check: Go to the last step, run the AI review, read the findings, and say which ones are useful and which are noise.
  Commit: `Add AI review step`

## Hands-on Checkpoints

- [x] Early usable behavior explored — after slice 3 (upload, download, and AI mapping)
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [x] Question and answer screen made handier with light colours — redesign done and verified (27 tests pass); waiting for the learner to retry it
- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: not started
Route and stops: not started
Edit outcome: not started
Reflection: not started
Activity mode: not started

## Revisions

- Questions cover Required plus Conditionally Required columns (130 in the sample) instead of Required only (9) — the template's `Data Definitions` flags 121 columns as Conditionally Required, including Metal Type, Stone Shape and Material, which the team actually fills; asking only the 9 strictly required would miss most of the work. Slice 4 and `spec.md > Question flow` apply this; columns already mapped from the master are not asked.
- Supported Python lowered from 3.11+ to 3.9+ — the learner's `streamlit` command runs under Python 3.9.13, where a `dict | None` type hint crashed the app at import; code now avoids 3.10+ syntax and `requirements.txt` must be installed into whichever Python runs `streamlit`.
- Validation treats only empty Required columns as blocking; dropdown mismatches and empty Conditionally Required columns are "check these" items — running the validator on the learner's hand-filled `Amazon_Ring upd_ (1).xlsm` (a file Amazon accepts) showed 6 false "not in dropdown" alarms, because the lists read from `Valid Values` are approximate (e.g. the file stores `full_update` where the list shows "Create or Replace (Full Update)"), and 90 conditional columns that legitimately don't apply.
- Parent rows (Parentage Level = parent) are exempt from the Product Id / Product Id Type check — Amazon parent listings carry no product id, and the answer key itself leaves them empty.
- A "Claude thinks this may be wrong" answer check can be overridden by pressing Continue again — a false rejection should never trap the user; the spec said "rejected", the hard rejection stays for dropdown values only.
- Values left in the template's first data row are shown as suggestions on the questions, never written automatically — the answer-key comparison showed they are leftovers from earlier listings (Ring Size 16, Stone Weight 0.5, a different Manufacturer), and the first version silently wrote them into all 608 rows; the hand-filled file had cleared 26 of the 42. All of those columns are now asked, with the suggestion pre-filled for the user to check.
- Columns the master fills in only some rows (e.g. Brand Name, empty on parent rows) are asked too, and the answer fills only the empty rows without overwriting master values — found when the validator flagged row 8 after the leftover defaults stopped hiding it.
- Answer-key result: the three answer modes explain 87 of 90 filled columns exactly; the output matches the hand-filled file in 93.8% of non-empty cells, all differences in Main/Other Image URL and Material, where the hand-filled file made editorial choices (a different main image, photos not in the master).
- Built-in listing rules added as slice 7 — the learner shared the rule logic of an earlier HTML tool (parent/child pairs, field mappings, brand and metal rules, hardcoded values) and asked to focus on rules while keeping the Python app and `.xlsm` output; where that prompt disagreed with the real template and hand-filled file (Variation Theme, Stone Creation Method, browse node format, Product Id Type, brand HSN codes) the rules follow the real files. Parent rows are taken from the master, which already contains them; generating parents from one-row-per-SKU masters is left for later.
- Answer sheet added as slice 8 — the learner found one-question-at-a-time too slow (about 95 questions) and accepted the recommendation of one pre-filled sheet, Claude proposals and answers remembered between runs; the earlier decision "one column per question" is replaced and the "saving answers across runs" item moves from Later into the build. Claude proposals are pre-filled only at 0.8+ confidence after a live comparison with the hand-filled file.
- Four-step layout added as slice 9 — the learner asked for the site to look better and be easier to handle; the single long page became four short steps. No product decision changed.
- AI review added as slice 10 — the learner asked for a last step validating the file with AI against the file's rules and regulations; the flow is now five steps. The live review showed the rules' Variation Theme `COLOR` was wrong for children that differ by ring size, so the rule became `COLOR/RING_SIZE` (the learner's earlier prompt said Size/Color). Live runs also exposed a reply cut off by the length limit, now handled.
