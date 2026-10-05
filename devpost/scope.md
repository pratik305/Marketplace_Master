---
doc: scope
status: approved
---

# Marketplace Template Filler

An AI-assisted tool that fills a marketplace's upload template (Amazon first) from a team's master product data, asking smart questions for whatever the master doesn't contain.

## The Unique Kernel
The agent doesn't just map columns. After mapping, it interviews the user column by column for the missing data: dropdown columns get the allowed values to pick from, and answers apply to all rows or per product/variant. It checks each answer against the template's own rules, so every mandatory column ends up filled and valid.

## Who It's For
The listing team. They take one master product file, which never has everything a marketplace needs, and fill a different, ever-changing VBA-enabled template by hand. They type entries and pick from dropdowns across 100+ products and their variants. It is slow, error-prone, and has to be checked against the rules afterwards.

## The Core Loop
1. The team uploads the master file and the marketplace template (rules sheet, data sheet, any extra sheets).
2. They hit one button. The AI reads both and proposes the column mapping.
3. For columns the master can't fill, the agent asks: what value, the same for all rows or different per product/variant? For dropdowns it offers the allowed values.
4. It validates answers against the template's rules.
5. It outputs the final filled template.

## Inspiration & Identity
Not established. Internal team tool; function over looks.

## Why This Matters to the Learner
It cuts tedious, mistake-prone manual work for their team's day-to-day listing work, and it's a chance to get the overall experience of building a real tool end to end.

## What "Working" Looks Like
Using an Amazon template and a master of up to ~500 rows: upload both, press the button, answer the agent's questions, and download a file that is the same VBA-enabled template format, filled in. All mandatory columns are filled, and the output matches the template's rules.
The "oh, that's cool" beat: hundreds of rows go from mostly empty to complete after a handful of smart questions.

## The POC Boundary
- Amazon only; one master file and one template per run (up to ~500 rows)
- Reads the template's rules sheet and data sheet(s)
- AI proposes the column mapping
- Question-and-answer flow for unmapped/missing columns: same-for-all or per-row, dropdown choices offered
- Validation of answers against the template rules; every mandatory column must be filled
- Output keeps the template's file format (VBA-enabled, macros and dropdowns intact)
- Master file columns (jewelry listings): CODE, BRAND, PLATFORM, CATEGORY, Sku Code, Sku Name, MRP, Selling Price, Sku Size, MP SKU CODE/STYLE ID, NET WEIGHT, GROSS Weight, Diamond Weight, Diamond Count, Diamond Shape, Care Instruction, Manufacture Name (x2), PACK CONTAINS, Country of Origin, Color, Certificate Type, Metal Stamp/Type/Material, Image Url 1-4, Gender, Description

## Later
- Other marketplaces (Flipkart, Etsy, etc.)
- Saving and reusing mappings and answers across runs and templates
- Automatic checking against the marketplace's own upload validator

## Explicitly Cut
Proposed for your review; nothing is cut that you haven't seen:
- User accounts, multi-user workflows and deployment: the PoC is for the team to try locally, and deployment is optional in this hackathon.
- Editing the template's VBA code: the macros must be preserved, not changed.
