# Changelog

## 1.8.0

- Migrated generation and reverse conversion flow to `seaf.company.ta.*` naming.
- Added directory input support in `config.yaml` for `data_yaml_file` (auto-load `*.yaml`/`*.yml`).
- Updated helper scripts (`scripts/scale_drawio_services.py`, `scripts/layout_tech_services.py`) for new schemas.
- Improved ISP placement on `Main Schema` to avoid overlaps by container-aware positioning.
- Added `auto_layout_grid` config flag in `seaf2drawio.py` to optionally run post-generation grid layout automatically.
- Extended auto-layout defaults to include Office pages and enforced UTF-8 execution for layout script calls on Windows.
- Fixed Office page placement: user devices now anchor to their connected network container; LAN pattern spacing tuned to keep networks within segment bounds.
- Updated docs with config variability, helper scripts usage, and sample command output.
- Updated dependency constraints in `requirements.txt`.
- **Breaking change:** SEAF1 (`seaf.ta.*`) support is disabled in this version.
