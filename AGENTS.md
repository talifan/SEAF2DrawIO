# AI Agent Guide (SEAF2DrawIO)

## Scope and Current Model
- Project uses **SEAF2 naming**: `seaf.company.ta.*`.
- SEAF1 compatibility (`seaf.ta.*`) is disabled in current release flow.
- Main conversion scripts:
  - `seaf2drawio.py` — YAML -> DrawIO.
  - `drawio2seaf.py` — DrawIO -> YAML.

## Repository Structure
- `lib/` — shared helpers (`seaf_drawio.py`, `link_manager.py`, `schemas.py`, `drawio_utils.py`).
- `data/patterns/` — layout patterns per page (`main.yaml`, `dc.yaml`, `office.yaml`).
- `data/example/` — sample input dataset.
- `scripts/` — helper automation (`layout_tech_services.py`, `scale_drawio_services.py`).
- `result/` — generated artifacts (`Sample_graph.drawio`, `seaf.yaml`).

## Build / Run Commands
- Install deps:
  - `python -m pip install -U pip`
  - `python -m pip install -r requirements.txt`
- Generate diagram:
  - `python -X utf8 seaf2drawio.py`
  - Optional output override: `python -X utf8 seaf2drawio.py -d result/out.drawio`
- Reverse conversion:
  - `python -X utf8 drawio2seaf.py`
- Windows tip:
  - use `python -X utf8 ...` (or `PYTHONUTF8=1`) for Cyrillic-safe output.

## Agent Rules for Code Changes
- Keep edits minimal and localized; avoid broad refactors unless requested.
- Prefer pattern updates in `data/patterns/*` for placement issues before touching core logic.
- If editing layout behavior, validate both:
  - DC pages (`Sber Cloud DC`, `VK DC`)
  - Office page (`Головной офис`)
- For generated artifacts, do not commit temporary outputs unless explicitly requested.

## Known Functional Notes
- Obsolete link cleanup is implemented in `lib/link_manager.py` and called from `seaf2drawio.py` before link creation.
- `seaf2drawio.py` supports optional post-layout automation via config:
  - `auto_layout_grid: true|false`
  - optional `auto_layout_script`, `auto_layout_diagram`, `auto_layout_filter`
- `scripts/layout_tech_services.py` primarily lays out technical services; if a page has none, it logs and skips.

## Pattern and Data Practical Notes
- Parent-first rendering is critical:
  - Objects with `parent_id` render only if parent already exists on page.
- Common mismatch traps:
  - Latin/Cyrillic lookalikes in enum values.
  - `ARM` vs `АРМ` (`АРМ` is expected in current schema/data).
- When adding categories, copy a nearby working pattern and adjust:
  - `schema`, `type`, `parent_id`, `x/y/w/h`, `algo`, `offset`, `deep`.

## Diagnostics Workflow
- Use generation verifier output (`Result: GENERATION MATCHES YAML (by schema)`).
- For mismatches, compare three sources:
  1) `data/example/*` values,
  2) schema definitions in `data/seaf_schema.yaml`,
  3) pattern constraints in `data/patterns/*`.

## Commit Guidance
- Commit message style: imperative, scoped, concise.
  - Example: `seaf2drawio: fix office user device placement by network parent`
