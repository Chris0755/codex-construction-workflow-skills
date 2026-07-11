---
name: strict-xlsx-reconciliation
description: Add audited records to a strict-format Excel reconciliation workbook while preserving its original visual layout, print settings, page-break preview, borders, formulas, merged cells, widths, and styles. Use when a user says an upstream Excel format must not change and only verified data should be added.
---

# Strict XLSX Reconciliation

## Core rule

Treat the upstream workbook as the visual and structural authority and the audited workbook as the data authority. Copy the upstream `.xlsx` first. Never overwrite it or rebuild the sheet through a generic export path.

## Workflow

1. Inspect both workbooks and identify records present in the audited source but absent from the target.
2. Confirm ambiguous material/specification mappings before writing.
3. Fill preformatted blank rows first. Insert the fewest possible rows only when capacity is exceeded.
4. When inserting rows, copy a neighboring detail-row style and shift subtotals, formulas, merged ranges, filters, signatures, and row breaks consistently.
5. Keep visible target naming even if source naming differs; use mappings only for recognition.
6. Verify with `scripts/verify_strict_xlsx.py` before delivery.

## Preservation checks

- `xl/styles.xml` and `xl/theme/theme1.xml` must match the original.
- Column definitions, page setup, print margins, and sheet view must match.
- Manually configured row breaks may shift only by the intentionally inserted row count.
- No formula error values may appear in workbook XML.
- New records must be present as a multiset, not merely by document number.

## Common pitfalls

- The blue page-preview boundary is controlled by print/view settings, not a normal cell border.
- Do not stretch columns outside the original print width to hide a page-break problem.
- Do not use a library save operation that rewrites the entire visual shell for a strict-format workbook; use targeted OOXML edits when necessary.
