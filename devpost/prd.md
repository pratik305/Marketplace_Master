---
doc: prd
status: approved
---

# Marketplace Template Filler — Product Requirements

A web tool that lets a marketplace-listing team upload a master product sheet and an Amazon template, confirm an AI-proposed column mapping, answer one question per missing column, and download the filled template in its original VBA-enabled format.
Source: `scope.md` (Unique Kernel, Core Loop, What "Working" Looks Like, POC Boundary).

## The Core Journey
1. **Open the tool.** The user sees two upload boxes: one for the master sheet, one for the marketplace template.
2. **Upload both files** and start the process (button).
3. **Review the mapping.** The AI reads both files (including the template's rules sheet and data sheet) and proposes which master column fills which template column. The user checks each pair: confirm it, or correct it. If the AI couldn't map a column, the user is asked to pick one or leave it unmapped.
4. **Answer questions, one template column at a time,** for every column the master doesn't supply. For each, the user gives a value, chooses "same for all rows" or a per-row source, or skips. Dropdown columns show the allowed values and the user must pick one.
5. **Validation and QC.** After all questions, the tool checks every row against the template's rules and shows what is still missing or invalid. Skipped mandatory columns are flagged here.
6. **Download** the filled template: same file format as the uploaded template (VBA-enabled), with the data filled in.

## Screens and Layout
A single-page flow with steps; one step is shown at a time.
- **Upload step:** two boxes side by side, "Master sheet" and "Template file", and a button to start.
- **Mapping step:** a table listing template columns, the proposed master column for each, and a way to confirm or change it.
- **Question step:** one template column per screen: the column name, why it matters (mandatory or optional), the input (free value or dropdown choices), the "same for all rows" option, and a Skip button. Shows progress (e.g. column 4 of 18).
- **Validation step:** a summary of rows filled, issues found (grouped by column), and mandatory columns still empty, each with a way to go back and fix. Download button.

## Look and Feel
Light colors, light background. Plain and functional; usability matters more than looks. No other visual direction was given.

## Features and Behavior

### Upload and reading files
- Accepts one master sheet (up to ~500 rows) and one Amazon template per run.
- Reads the template's rules sheet and data sheet(s) to learn column names, mandatory columns, dropdown values and rules.
- Master columns are the jewelry listing columns listed in `scope.md > The POC Boundary`.

### Column mapping
- The AI proposes the mapping; the user validates it ("is this the right column or not") and corrects wrong ones.
- Most values, especially numeric ones, come straight from the master through the mapping.
- Acceptance criteria:
  - [ ] After upload, every template column shows either a proposed master column or "not mapped".
  - [ ] The user can change any pair before moving on.

### Four-step layout
Changed after the learner asked for a better-looking, easier-to-handle site. Replaces the single long page in `Screens and Layout`.
- A header banner, a clickable step bar with a progress line (**1 Upload, 2 Prepare, 3 Answers, 4 Check & download**; finished steps show a tick; steps after Upload unlock once the files are read) and summary chips (rows, columns filled by rules, columns mapped, answers given).
- **Upload**: two upload cards, a Read files button, and what the tool understood. **Prepare**: tabs for the built-in rules and the column mapping. **Answers**: the answer sheet. **Check & download**: validation, then one large Download button.
- Back and Continue buttons on every step; "Fix this" in the validation list jumps back to the Answers step.
- Light colours throughout, bigger buttons and clear spacing (usability over decoration).
- Acceptance criteria:
  - [ ] Before files are read only Upload is available; reading valid files moves to Prepare.
  - [ ] Each step shows only its own content; Back, Continue and the step bar all navigate.
  - [ ] "Fix this" on a validation item returns to the Answers step.

### Built-in listing rules
Source: the learner's rule logic (parent/child rows, product type, metal, units, fixed values), checked against the hand-filled Amazon file. Implements `scope.md > The POC Boundary` (built-in listing rules).
- Before the mapping and questions, the tool applies the rules in `rules/amazon_in_jewellery.json`. The user can switch them off.
- Rules fill: parent/child markers and Parent SKU; Product Type and browse node from the category; Metal Type, Metal Stamp, Material and Color Map from the metal stamp and colour; units; fixed values (Listing Action, Gem Type, Stone Creation Method, ...); translated values (e.g. "IGI Certificate" -> "IGI", "Women" -> "female"); copies of master columns (price, MRP, images, bullet points).
- Parent rows take their first child's value for family attributes; child-only columns (images, Ring Size, weights, Material, Parent SKU) stay blank on parents.
- A rule value replaces the raw master value in its column. Columns fully filled by rules are not asked.
- Every rule value is checked against the template's dropdown list; values the template would not accept are listed for the user.
- Acceptance criteria:
  - [ ] The rules screen shows how many columns the rules filled and the parent/child row counts.
  - [ ] Against the learner's hand-filled file, the rule output matches in at least 94% of the cells it fills (differences are editorial picks such as image URLs).
  - [ ] Columns covered by rules do not appear in the questions; the question count is lower than without rules.
  - [ ] A rule value outside a column's dropdown is listed instead of silently written.
  - [ ] "Skip all conditionally required" skips every unanswered conditionally required question and leaves required ones.

### Answer sheet (replaces answering one column at a time)
Changed after the learner found one-question-at-a-time too slow for a long list. Implements `scope.md > The Core Loop` (ask about what is missing) in a faster shape.
- All remaining columns appear on one screen, grouped in tabs by the template's own sections, one row per column, with the right input (dropdown for dropdown columns, text otherwise).
- Rows are pre-filled, in this order: the user's last answer, answers saved from an earlier run, a Claude proposal (only when Claude is at least 0.8 confident), the template's own first-row suggestion. A less confident Claude proposal is shown as a hint only.
- Nothing is used until the user presses **Apply all answers**. A blank row means skip; skipped required columns are flagged in the validation step.
- **Let Claude propose answers** fills blank rows; **Remember these answers for next time** (on by default) saves them to a local, git-ignored file so the next run of the template starts pre-filled.
- A separate box handles answers that differ per product: choose the template column and the master column it depends on, then fill one value per entry.
- The one-at-a-time screen stays available as an option.
- Acceptance criteria:
  - [ ] The sheet shows every remaining column on one screen (in tabs) with no more than one button press to apply them all.
  - [ ] Template suggestions and saved answers pre-fill their rows; Claude proposals below 0.8 confidence are not pre-filled.
  - [ ] Apply stores a value for each filled row and marks blank rows skipped.
  - [ ] With remembering on, a second run of the same template pre-fills the saved answers.
  - [ ] Without an API key the Claude button explains why and nothing breaks.

### Asking about missing columns
- Only columns that are not mapped from the master (or are empty in it) generate a question.
- One column at a time. The agent explains the column and asks for the value.
- The user can say whether the value is the same for all rows or varies; when it varies, the value comes from a master column or is entered per product/variant group (see Open Questions).
- Dropdown columns: the user must select one of the allowed values; free text is not accepted.
- The agent uses its own judgment, plus the template rules, to judge whether the answer is right; a bad answer is rejected with the reason and the user is asked again.
- The user may skip any column. Skipping is allowed even for mandatory columns, but they're flagged at the end.
- Acceptance criteria:
  - [ ] Only one column question is visible at a time, with progress shown.
  - [ ] A dropdown column offers exactly the template's allowed values.
  - [ ] An invalid answer is not accepted; the reason is shown.
  - [ ] Skip moves to the next column.

### Validation and QC
- After the last question, every row is checked against the template rules.
- Skipped or still-empty mandatory columns are flagged; the user can go back to fill them.
- Acceptance criteria:
  - [ ] The summary lists each remaining problem with its column and row count.
  - [ ] When all mandatory columns are filled and valid, the summary shows no remaining problems.

### Output
- The output file has the same format as the uploaded template, VBA-enabled, with macros and dropdowns intact, and the data filled in.
- Acceptance criteria:
  - [ ] The downloaded file opens in Excel as the same template with the rows filled.
  - [ ] All mandatory columns are filled for all rows (when the user answered everything).

## States and Boundaries
- **First use / before upload** — two empty upload boxes; the start button is disabled until both files are added.
- **Mapping unclear** — unmapped template columns are shown as "not mapped" and sent to the questions.
- **Skipped mandatory column** — allowed, but flagged at validation with a prompt to fill it.
- **Invalid answer** — rejected with the reason; the same question stays on screen.
- **Unusable file (assumption)** — if a file can't be read or the template has no rules sheet, the tool shows a clear error and lets the user upload again.
- **Nothing persists (assumption)** — closing the page loses progress; each run starts fresh.

## Product Decisions
- Two upload boxes, mapping reviewed by the user — the AI proposes but the human confirms the mapping.
- One column per question — keeps the interaction simple for a team of listers.
- Dropdown columns force a pick from the allowed values — values must match the template.
- Skipping allowed, mandatory gaps flagged at the end — don't block the flow, but never ship a hidden gap.
- Final QC with missing items shown — the user validates before downloading.
- Light, plain UI — usability over looks.
- Output is the same VBA-enabled template format — it must be directly uploadable.

## What We're Building
Everything in Core Journey, Features and Behavior, and States and Boundaries above, for Amazon only.

## Deferred From the POC
- Other marketplaces: each has its own template structure.
- Saving and reusing mappings and answers across runs: needs storage.
- Automatic check against the marketplace's own validator.
- Accounts, multi-user workflows, deployment.

## Possible Later Enhancements
Remembering past answers per product category; bulk apply of rules; a history of runs.

## Non-Goals
- Editing the template's VBA code: macros are preserved, not changed.
- Producing files for marketplaces other than Amazon in this POC.

## Open Questions
- **How does the user supply values that differ per product/variant?** (Assumption for now: the value comes from a master column, or the user enters it for a group of rows, e.g. by CATEGORY.) Must be settled before `4-spec`.
- **Unusable files and no persistence** are assumptions, not decisions: confirm or change them.

## Revision: built-in rules
- Added after the learner shared the rule logic of an earlier tool (parent/child pairs, field mappings, brand and metal rules, hardcoded values). The learner chose to keep the Python/Streamlit app and the `.xlsm` output (not the single-file HTML tool with CSV output) and to focus on the rules. Where the earlier prompt and the real files disagree (Variation Theme `Size/Color` vs `COLOR`, `Lab-grown` vs `Lab-Created`, browse node id vs path, Product Id Type `SKU` vs `GTIN Exempt`, brand HSN codes vs the master's `71131914`) the rules follow the real template and hand-filled file.

## Revision: answer sheet
- The learner found answering about 95 questions one at a time too slow and accepted a recommendation: one pre-filled answer sheet, Claude proposals, and answers remembered between runs. This changes the earlier decision "one column per question" and moves "saving answers across runs" from Later into the build.

## Revision: four-step layout
- The learner asked for the site to look better and be easier to handle. The single long page became four short steps with a step bar, summary chips and larger light-coloured controls.
