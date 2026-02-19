# Repository Guidelines

## Project Structure & Module Organization
- `seaf2drawio.py` — generate DrawIO diagrams from SEAF YAML data using patterns in `data/patterns/`.
- `drawio2seaf.py` — parse DrawIO back into YAML using `data/seaf_schema.yaml`.
- `lib/` — shared helpers (`seaf_drawio.py`, `link_manager.py`).
- `data/` — example YAML inputs, DrawIO templates, schema, and patterns; `data/example/` contains sample datasets.
- `result/` — build artifacts (e.g., `Sample_graph.drawio`, `seaf.yaml`).

## Build, Test, and Development Commands
- Install Python deps (3.9+):
  - `python -m pip install -U pip`
  - `python -m pip install N2G PyYAML deepmerge`
- Generate diagram:
  - `python -X utf8 seaf2drawio.py` (uses `config.yaml`), or
  - `python -X utf8 seaf2drawio.py -s data/example/...yaml -d result/out.drawio -p data/base.drawio`
- Reverse conversion to YAML:
  - `python -X utf8 drawio2seaf.py -s result/out.drawio -p data/seaf_schema.yaml -d result/seaf.yaml`
- Windows tip: set `PYTHONUTF8=1` if you see encoding issues.

## Coding Style & Naming Conventions
- Python, 4‑space indentation, UTF‑8 source.
- Prefer explicit, descriptive names (`snake_case` for functions/vars, `CapWords` for classes).
- Keep changes minimal and localized; avoid unrelated refactors.
- Follow existing patterns for XML string templates and YAML merging.

## Testing Guidelines
- No formal test suite. Validate by:
  - Running generation and ensuring `result/*.drawio` opens and pages render.
  - Checking console output is free of unexpected errors (informational lines only).
  - For changes to patterns, verify objects appear on expected pages and do not overlap.

## Commit & Pull Request Guidelines
- Commit messages: imperative mood, concise scope + summary.
  - Example: `seaf2drawio: handle WAN segment arrays; reduce log noise`
- PRs should include:
  - What changed and why, affected files/modules.
  - Repro/verify steps (commands) and before/after notes (optionally attach `.drawio`).
  - Any configuration or data updates (`config.yaml`, `data/patterns/*`, `data/example/*`).

## Security & Configuration Tips
- Do not commit secrets; `config.yaml` should reference local files only.
- Keep inputs in `data/example/`; write artifacts to `result/`.
- Large edits to patterns can impact layout across pages—test both DC and Office pages.


## SEAF TA Patterns: Practical Notes (for future agents)

- UTF‑8 everywhere
  - Always run with UTF‑8 output on Windows: `python -X utf8 seaf2drawio.py` or set `PYTHONUTF8=1`.
  - Console/log messages may include Cyrillic; without UTF‑8 you may get encode errors.

- Diagnostics triage loop (3‑line check)
  - When `seaf2drawio.py` reports “Diagnostics for missing items”, for each item compare:
    1) Example value (from `data/example/*`), 2) Schema enum/title (from `_metamodel_/seaf-core/entities/*`), 3) What the script/patterns expect (by category/type in `data/patterns/*`).
  - Decide where to fix: patterns vs examples vs schema. Prefer aligning patterns to the schema if examples already match schema.

- Common mismatches and fixes
  - Latin vs Cyrillic lookalikes: `Cерверы…` (Latin “C”) vs `Серверы…` (Cyrillic “С”). Keep schema + examples consistent; update patterns to match exactly.
  - Device type: `ARM` vs `АРМ`. The schema uses Cyrillic `АРМ`; align patterns to `АРМ`.
  - compute_service dns/dhcp/ntp: examples must include `service_type: "Управление сетевым адресным пространством (DHCP, DNS и т.д.)"` otherwise items won’t be classified by patterns.

- Ordering matters with parent_id
  - Many patterns rely on `parent_id` fields (e.g., `network_connection`, `segment`). Objects are rendered only after their parent appears on the page.
  - If a category does not render even though data and schema are correct, place its pattern block after the parent’s pattern blocks in `data/patterns/*`.
  - Example: compute_service category “Шлюз, Балансировщик, прокси”. Use the block `ta_services_proxy_compute_fallback` placed after network sections so that `parent_id='network_connection'` is present.

- About `ta_services_proxy_compute_fallback`
  - Purpose: robust placement for `seaf.ta.services.compute_service` with `service_type="Шлюз, Балансировщик, прокси"` after network objects are drawn.
  - Why: the generator adds a child only if the parent already exists on the page; this block guarantees the correct order.
  - Keep a single active block; remove/avoid duplicates (any `*_disabled` variants are cleanup targets).

- Pattern hygiene
  - Avoid duplicate top‑level keys in pattern YAML (they error the loader).
  - Prefer adding new categories by copying a nearby working block and adjusting `type: 'service_type:…'` and coordinates `x/y` to fit the existing grid.
  - Test both DC (`data/patterns/dc.yaml`) and Office (`data/patterns/office.yaml`) pages; coordinates differ between pages.
