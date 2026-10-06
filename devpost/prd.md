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
