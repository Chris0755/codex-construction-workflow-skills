# Construction workflow skills for Codex

Reusable Codex skills for two repetitive, error-prone construction-material workflows:

- `weighbridge-folder-to-excel`: turn a folder of weighbridge slip images into a reviewed Excel copy without overwriting the template.
- `strict-xlsx-reconciliation`: add audited records to a strict upstream reconciliation workbook while preserving the workbook's visual shell and print layout.

## Why this exists

These workflows are designed for teams that still rely on supplier spreadsheets, ticket photos, and fixed-format settlement workbooks. The skills keep business-specific details in local configuration instead of hard-coding company names, file paths, plates, supplier aliases, or real templates.

## Install

Copy the skill directories you want into `~/.codex/skills/`, then start a new Codex task. Keep real templates, OCR images, mappings, and customer data outside this repository.

## Configure safely

Start from `skills/weighbridge-folder-to-excel/references/workflow-config.example.json`. Pass paths to the template and optional plate/team mapping when running the helper scripts. Do not commit real `.xlsx` files, ticket photos, or production OCR output.

## Maintainer roadmap

1. Add synthetic ticket fixtures and regression tests.
2. Add more station and workbook-layout configurations.
3. Improve OCR conflict detection and confidence reporting.
4. Keep the skills compatible with new Codex releases.

## License

MIT. See [LICENSE](LICENSE).
