# Миграция SEAF2DrawIO на новое именование сущностей

## Цель работы

Перевести скрипт `seaf2drawio.py` и все связанные файлы конфигурации и шаблонов с устаревшего
именования SEAF2-сущностей (`seaf.ta.*`) на актуальное (`seaf.company.ta.*`), принятое в
датасетах `data/seaf2_example/`.

**Ожидаемый результат:** запуск `python seaf2drawio.py` с данными из `data/seaf2_example/`
должен завершаться строкой:
```
Result: GENERATION MATCHES YAML (by schema)
```
и генерировать корректный файл `result/Sample_graph.drawio`.

---

## Суть изменений схем (таблица маппинга)

| Старое (`seaf.ta.*`) | Новое (`seaf.company.ta.*`) |
|---|---|
| `seaf.ta.services.dc_region` | `seaf.company.ta.services.dc_regions` |
| `seaf.ta.services.dc_az` | `seaf.company.ta.services.dc_azs` |
| `seaf.ta.services.dc` | `seaf.company.ta.services.dcs` |
| `seaf.ta.services.office` | `seaf.company.ta.services.dc_offices` |
| `seaf.ta.services.network_segment` | `seaf.company.ta.services.network_segments` |
| `seaf.ta.services.network` | `seaf.company.ta.services.networks` |
| `seaf.ta.services.network_links` | `seaf.company.ta.services.network_links` |
| `seaf.ta.components.network` | `seaf.company.ta.components.networks` |
| `seaf.ta.services.cluster_virtualization` | `seaf.company.ta.services.cluster_virtualizations` |
| `seaf.ta.services.cluster` | `seaf.company.ta.services.compute_services` (объединён!) |
| `seaf.ta.services.compute_service` | `seaf.company.ta.services.compute_services` |
| `seaf.ta.services.k8s` | `seaf.company.ta.services.k8s` |
| `seaf.ta.services.backup` | `seaf.company.ta.services.backups` |
| `seaf.ta.services.monitoring` | `seaf.company.ta.services.monitorings` |
| `seaf.ta.components.server` | `seaf.company.ta.components.servers` |
| `seaf.ta.components.user_device` | `seaf.company.ta.components.user_devices` |
| `seaf.ta.services.software` | `seaf.company.ta.services.softwares` |
| `seaf.ta.services.storage` | `seaf.company.ta.services.storages` |
| `seaf.ta.services.hw_storage` | `seaf.company.ta.services.hw_storages` |
| `seaf.ta.services.kb` | `seaf.company.ta.services.kb` |
| `seaf.ta.services.logical_link` | `seaf.company.ta.services.logical_links` |
| `seaf.ta.services.environment` | `seaf.company.ta.services.environments` |
| `seaf.ta.services.stand` | `seaf.company.ta.services.stands` |
| `seaf.ta.components.k8s.namespace` | `seaf.company.ta.components.k8s.namespaces` |
| `seaf.ta.components.k8s.node` | `seaf.company.ta.components.k8s.nodes` |
| `seaf.ta.components.k8s.deployment` | `seaf.company.ta.components.k8s.deployments` |
| `seaf.ta.components.k8s.hpa` | `seaf.company.ta.components.k8s.hpa` |

Дополнительно изменились строки **type** у сетевых компонентов (`seaf.company.ta.components.networks`):

| Старый тип | Новый тип |
|---|---|
| `type:МСЭ` | `type:Межсетевой экран (файрвол)` |
| `type:Маршрутизатор` | `type:Маршрутизатор (роутер)` |
| `type:Контроллер WiFi` | `type:Точка доступа (Wi-Fi)` |
| _(отсутствовал)_ | `type:Балансировщик нагрузки (Load Balancer)` |

---

## Статус выполнения

### ✅ Выполнено

| Файл | Изменение | Статус |
|---|---|---|
| `seaf2drawio.py` | Обновлены 3 хардкодных схемы: `root_object`, `network_links`, `remove_obsolete_links` | ✅ Сделано |
| `config.yaml` | Список `data_yaml_file` переключён с `data/example/` на `data/seaf2_example/`; учтены переименования и объединения файлов | ✅ Сделано |
| `data/patterns/main.yaml` | Все поля `schema:` обновлены с `seaf.ta.*` на `seaf.company.ta.*` | ✅ Сделано |
| `data/patterns/dc.yaml` | Все поля `schema:` обновлены; строки `type:` для сетевых устройств исправлены; добавлен паттерн `load_balancer` | ✅ Сделано |
| `data/patterns/office.yaml` | Все поля `schema:` обновлены; строки `type:` для сетевых устройств исправлены | ✅ Сделано |
| `lib/link_manager.py` | Верификация `logical_links` расширена на новое имя схемы `seaf.company.ta.services.logical_links` | ✅ Сделано |
| **Финализация** | Запуск скрипта, проверка вывода `GENERATION MATCHES YAML`, проверка отрисовки LB и logical links | ✅ Сделано |

### ❌ Осталось

*Все задачи выполнены.*

---

## Изменения входных файлов данных (`config.yaml`)

| Старый файл | Новый файл | Примечание |
|---|---|---|
| `data/example/dc_region.yaml` | `data/seaf2_example/dc_region.yaml` | |
| `data/example/dc_az.yaml` | `data/seaf2_example/dc_az.yaml` | |
| `data/example/dc.yaml` | `data/seaf2_example/dc.yaml` | |
| `data/example/office.yaml` | `data/seaf2_example/dc_office.yaml` | Переименован |
| `data/example/network_segment.yaml` | `data/seaf2_example/network_segment.yaml` | |
| `data/example/networks_dc01.yaml` + `networks_dc02.yaml` + `networks_office.yaml` | `data/seaf2_example/network.yaml` | Объединены в один файл |
| `data/example/components_network_dc01/02/office.yaml` | `data/seaf2_example/network_component.yaml` | Объединены |
| `data/example/network_links.yaml` | `data/seaf2_example/network_links.yaml` | |
| `data/example/cluster_virtualization.yaml` | `data/seaf2_example/cluster_virtualization.yaml` | |
| `data/example/cluster.yaml` | _(удалён)_ | Данные перенесены в `compute_service.yaml` |
| `data/example/compute_service.yaml` | `data/seaf2_example/compute_service.yaml` | |
| `data/example/k8s.yaml` | `data/seaf2_example/k8s.yaml` | |
| `data/example/k8s_namespace.yaml` | `data/seaf2_example/k8s_namespaces.yaml` | Переименован |
| `data/example/k8s_node.yaml` | `data/seaf2_example/k8s_nodes.yaml` | Переименован |
| `data/example/k8s_deployment.yaml` | `data/seaf2_example/k8s_deployments.yaml` | Переименован |
| `data/example/k8s_hpa.yaml` | `data/seaf2_example/k8s_hpa.yaml` | |
| `data/example/hw_storage.yaml` | `data/seaf2_example/hw_storage.yaml` | |
| `data/example/storage.yaml` | `data/seaf2_example/storage.yaml` | |
| `data/example/server.yaml` | `data/seaf2_example/server.yaml` | |
| `data/example/monitoring.yaml` | `data/seaf2_example/monitoring.yaml` | |
| `data/example/backup.yaml` | `data/seaf2_example/backup.yaml` | |
| `data/example/software.yaml` | `data/seaf2_example/software.yaml` | |
| `data/example/user_device.yaml` | `data/seaf2_example/user_device.yaml` | |
| `data/example/logical_link.yaml` | `data/seaf2_example/logical_link.yaml` | |
| `data/example/kb.yaml` | `data/seaf2_example/kb.yaml` | |

---

## Методы проверки

### 1. Автоматическая — встроенная верификация скрипта

```powershell
cd c:\Users\aaksi\Documents\SEAF2DrawIO
python seaf2drawio.py
```

**Критерий успеха:**
```
Result: GENERATION MATCHES YAML (by schema)
```

Скрипт выводит подробный отчёт: для каждой схемы показывает `expected` (кол-во объектов в YAML)
и `drawn_unique` (кол-во нарисованных). Совпадение по всем схемам → OK.

**Если есть MISMATCH** — смотреть секцию `Diagnostics for missing items`:
- `type='X' | expected: Y, Z` — объект не попал ни в один паттерн, тип `X` не объявлен
- `parent 'segment' not present on pages` — родительский объект не нарисован (цепочка зависимостей)
- `no rule matched` — объект вообще не соответствует ни одному паттерну

### 2. Ручная — визуальная проверка диаграммы

Открыть `result/Sample_graph.drawio` в [draw.io](https://app.diagrams.net/) и убедиться:
1. Страница **Main Schema** — регионы, ЦОДы, офис, глобальные сети (ISP, WAN)
2. Страницы **Sber Cloud DC** и **VK DC** — сегменты безопасности, сети, сетевые устройства, серверы, K8s, мониторинг, бекап
3. Страница **Головной офис** — сети офиса, пользовательские устройства
4. **Связи** между объектами нарисованы (синие линии для сетевых связей, зелёные/красные для logical_links)

### 3. Сравнение с baseline

Сравнить `result/Sample_graph.drawio` с архивным файлом `result/Sample_graph_example_baseline.drawio`
(сохранён до начала миграции) — топология должна быть эквивалентна, только с новыми данными.
