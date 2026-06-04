# Changelog

## Unreleased

- Added optional common location page generation via `common_location_page` and `--common-location-page`.
- The common page stacks generated office and DC diagrams vertically, deduplicates provider networks from Internet-facing zones, and reconnects copied links to shared provider nodes.
- The common page now redraws `logical_links`, including inter-location routes, while individual pages skip routes with endpoints outside the page.
- Common-page `logical_links` now resolve all visual copies of duplicated SEAF objects, so links to stretched clusters are not collapsed to the first copied endpoint.
- Untagged `logical_links` are moved to a separate visible foreground layer after generation, so they render above zone rectangles and the template `Links` layer.
- Documented common page configuration, logical link `topology`, and tag-based logical link layers.

## 1.8.0

- Migrated generation and reverse conversion flow to `seaf.company.ta.*` naming.
- Added `topology` support for logical links in `seaf2drawio.py`: `star` keeps source-to-all-targets rendering, while `chain` renders ordered point-to-point routes through the `target` list.
- Added logging for logical links with missing or unknown `topology` and warnings for links that cannot be drawn because an endpoint is absent from the current page.
- Added directory input support in `config.yaml` for `data_yaml_file` (auto-load `*.yaml`/`*.yml`).
- Updated helper scripts (`scripts/scale_drawio_services.py`, `scripts/layout_tech_services.py`) for new schemas.
- Improved ISP placement on `Main Schema` to avoid overlaps by container-aware positioning.
- Added `auto_layout_grid` config flag in `seaf2drawio.py` to optionally run post-generation grid layout automatically.
- Extended auto-layout defaults to include Office pages and enforced UTF-8 execution for layout script calls on Windows.
- Fixed Office page placement: user devices now anchor to their connected network container; LAN pattern spacing tuned to keep networks within segment bounds.
- Updated docs with config variability, helper scripts usage, and sample command output.
- Updated dependency constraints in `requirements.txt`.
- **Breaking change:** SEAF1 (`seaf.ta.*`) support is disabled in this version.
