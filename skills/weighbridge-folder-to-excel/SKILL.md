---
name: weighbridge-folder-to-excel
description: Create a verified Excel copy from a folder of weighbridge-slip images. Use when Codex needs to OCR ticket photos, conservatively normalize ticket fields, fill a user-provided Excel template without changing it, and track which folders have been processed.
---

# Weighbridge Folder To Excel

## Contract

Treat the photo folder as input and the supplied Excel workbook as a read-only template. Save a new workbook in the requested output folder. Preserve uncertain fields as `待核`; never invent a number, plate, document number, material, or supplier.

## Required inputs

Ask for or discover:

1. One photo folder.
2. A template workbook path.
3. The starting data row and sheet when the template is not self-evident.
4. An optional plate-to-team workbook.
5. A local workflow configuration. Start from `references/workflow-config.example.json`.

Never include these production assets in a public repository.

## Workflow

1. Check the folder has images and has not already been recorded in the local processed-folder ledger.
2. Run a local OCR engine and save OCR JSONL beside the output temporarily.
3. Parse the JSONL with `scripts/parse_ocr_jsonl.py`, passing `--config` when supplier aliases, document corrections, material rules, or default station names are required.
4. Fill a copy of the template with `scripts/fill_excel_template.py`. Always pass `--template`; do not use a hard-coded user path.
5. Reopen the output and verify row count, formulas, `待核` notes, and document-number duplication.
6. Update the processed-folder ledger only after verification succeeds.

## Data rules

- Prefer printed station specifications over a noisy OCR material guess.
- Convert kg-looking weights to tons only when the ticket context supports it.
- Prefer a locally consistent gross minus tare equals net group.
- Use the strongest cross-orientation value cluster; do not concatenate OCR orientations and take the first match.
- Make supplier aliases, document-prefix repairs, and material mappings configuration, not code.
- Keep the template's formulas unless the user explicitly gives a settlement formula.

## Helpers

```bash
python3 scripts/parse_ocr_jsonl.py \
  --ocr-jsonl /path/to/ocr.jsonl \
  --photo-folder /path/to/photos \
  --config references/workflow-config.example.json \
  --output /path/to/rows.json

python3 scripts/fill_excel_template.py \
  --rows /path/to/rows.json \
  --photo-folder /path/to/photos \
  --template /path/to/template.xlsx \
  --layout-config /path/to/layout.json \
  --plate-map /path/to/plate-map.xlsx
```

## Ask first

Pause before generating output when the folder mixes projects/dates, no images are present, the template is missing, the layout is unknown, or most essential OCR fields are uncertain.
