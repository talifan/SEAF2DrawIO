## Назначение
`scripts/layout_tech_services.py` — постпроцессор, который дополняет результат `seaf2drawio.py`. Он собирает технические сервисы (compute, k8s, monitoring, kb и т.п.), группирует их по типам и раскладывает по сегментам ЦОДа. Внутри сегмента слева остаются сети, справа строятся сетки техсервисов, а рамка ЦОДа автоматически расширяется, чтобы вмещать все сегменты. Скрипт не зависит от конкретных префиксов (`flix.*`) и работает для всех страниц типа “<…> DC”.

## Быстрый запуск
```powershell
# 1. Сгенерировать базовую схему (используется config.yaml)
python -X utf8 seaf2drawio.py

# 2. Разложить техсервисы на всех DC-листах
python -X utf8 scripts/layout_tech_services.py --diagram all

# 3. (Опционально) собрать «большую» схему для стресс‑теста
python -X utf8 scripts/scale_drawio_services.py --diagram all --factor 5 -o result/Sample_graph_stress.drawio
python -X utf8 scripts/layout_tech_services.py --diagram all -i result/Sample_graph_stress.drawio
```
Ключевые параметры CLI:
- `scripts/scale_drawio_services.py`
  - `--input`/`--output` — исходный `.drawio` и файл с результатом (по умолчанию `result/Sample_graph_stress.drawio`).
  - `--diagram`/`--diagram-filter` — какие страницы дублировать (логика такая же, как у скрипта раскладки).
  - `--factor` — во сколько раз клонировать техсервисы (минимум 2).
- `scripts/layout_tech_services.py`
  - `--diagram all` — обработать все страницы, название которых содержит слова из `--diagram-filter` (по умолчанию `DC,ЦОД`). Можно задать явный список: `--diagram "Sber Cloud DC,VK DC"`.
  - `--diagram-filter` — фильтр по подстроке, если имена страниц отличаются (например, добавить `DC1`).
  - `--segment-id`, `--neighbor-segment-id` — запасные ID (нужны только если в данных вообще нет `segment`/`network_connection`).
- `--dc-container-id` — вершина рамки ЦОДа (в паттерне это `001`).

## Что делает скрипт
1. **Сбор данных**: `collect_cells` индексирует все `object/mxCell`, `build_connection_segment_index` связывает `network_connection` → `segment`, `build_segment_zone_index` строит карту `(zone, location) -> segment_id`.
2. **Группировка**: для схем из `TARGET_SCHEMAS` определяется сегмент (из `segment`, из сетевых подключений), рассчитывается размер ноды и ключ группы (`service_type`, `technology`, `tag` и т.д.).
3. **Расположение**: в каждом сегменте формируются контейнеры `tech_group_*`. Координаты считаются относительно сетей:  
   - `layout_mode="append_right"` — колонка сервисов справа от сетей.  
   - `stack_down` — сервисы добавляются снизу.  
   Высота сегмента увеличивается с запасом (`BOTTOM_MARGIN`), ширина — по факту максимального контейнера.
4. **Сдвиг соседей** (`ZONE_RULES`): INT-NET толкает INT-SECURITY, DMZ тянет вниз INT-WAN-EDGE и отодвигает INT-NET, INET-EDGE держит колонку слева.
5. **Пересчёт рамки ЦОДа**: ширина/высота `001` обновляется по максимальным `segment_x + width` и `segment_y + height`, поэтому «Защищённый сегмент данных» остаётся внутри рамки даже на stress‑схеме.

## Как работают подсказки для КБ
`SECURITY_ZONE_HINTS` привязывает объекты `seaf.ta.services.kb` по ключевым словам. Логика:
- Если сегмент уже найден по сетям (`derived_from_network=True`), подсказка **не** переопределяет его. WAF, привязанный к Internet, останется там же.
- Если сегмента нет (например, `segment` пустой), хинт ищет подходящий сегмент той же локации через `zone_index[(zone, location)]`.
- Список ключевых слов можно расширять, например, добавить новые типы IPS/IDS.

## Проверки
После каждого запуска стоит открыть `result/Sample_graph.drawio` и убедиться, что:
- Internet/Транспортная сеть/INET-EDGE/EXT WAN-EDGE стоят в одной колонке слева и не наезжают на DMZ.
- DMZ и INT WAN-EDGE находятся внутри рамки ЦОДа, INT-WAN строго под DMZ.
- INT-NET и INT-SECURITY-NET занимают правую часть, а «Защищённый сегмент данных» не выпадает за рамку.
- На stress‑версии (`result/Sample_graph_stress.drawio`) сегменты расширились, но порядок сохранился.

## Расширение логики
- **Новые сегменты**: добавить блок в `ZONE_RULES` (какой режим, ширина, кого сдвигать/подкладывать).
- **Новая схема**: дописать её в `TARGET_SCHEMAS`, указать поля `group_by`, `auto_segment`.
- **Дополнительные фильтры страниц**: заменить `--diagram-filter` или передать список через `--diagram`.
- **Настройка контейнеров**: отредактировать константы (`NODE_W`, `MAX_COLS`, `GAP_X/Y`) в начале скрипта.
