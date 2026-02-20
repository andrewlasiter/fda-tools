# eSTAR Template PDFs

This directory is reserved for bundled eSTAR template PDFs from FDA.gov.

## Templates

| Template | Version | Download URL |
|----------|---------|-------------|
| nIVD eSTAR | v6 | https://www.fda.gov/media/174458/download |
| IVD eSTAR | v6 | https://www.fda.gov/media/174459/download |
| PreSTAR | v2 | https://www.fda.gov/media/169327/download |

## Purpose

These templates are used by `estar_xml.py` for:
1. XFA field name discovery (extract field IDs programmatically)
2. XML schema validation during export
3. User convenience (don't need to find/download templates)

## Note

Due to file size, the actual PDF templates are not bundled in the git repository.
Download them from the FDA URLs above or use `/fda:configure` to set up auto-download.
