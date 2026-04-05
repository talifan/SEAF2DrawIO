# Backlog: manual_drawio -> SEAF YAML

## v0.3.1 — Глубокое исправление иерархии и сервисов

### P0 — Исправлено
- [x] Разделена внутренняя и внешняя модель: введен признак `is_external` для сегментов типа Internet.
- [x] Валидатор расширен на все 10 YAML файлов v0.3.
- [x] Форма `location` приведена к массиву `[]` для всех сущностей.
- [x] Исправлен schema key для `storage` -> `storages`.
- [x] Наполнено минимальное количество полей для сервисов (`service_type`, `technology`).

### P1 — Качество распознавания
- [x] Типизация: Неизвестных типов < 10% (OK). Добавлены правила для ФПСУ, SOC, EDR, Backup.
- [x] Чистка: Расширен список шума (АС, Согласовано, СБЕР).
- [x] OID: Внедрена детерминированная схема `имя.локация` (dmz.dc_rented).
- [x] Транзитивность: Локации наследуются от сегментов корректно.

---

## Замечания по повторной проверке результата

### Что стало лучше
- [x] На свежем прогоне снова стабильно извлекаются 3 локации.
- [x] Для `network` заполнены `segment` и `location`, а у `network_component` / сервисов `location` теперь пишется массивом.
- [x] `storage.yaml` теперь генерируется с `seaf.company.ta.services.storages`.

### P0 — блокеры до закрытия `v0.3.1`
- [x] Пересмотреть статус `v0.3.1 DONE`: свежий запуск конвертера возвращает `⚠️ Структурная валидация пройдена, но Quality Gates НЕ выполнены`, потому что `93.8%` компонентов не имеют `network_connection`. Это прямо противоречит пункту “Quality Gates пройдены”.
- [x] Разнести `backup` в отдельный `backup.yaml` / `seaf.company.ta.services.backups`. Сейчас объекты с OID `project.backup.*` попадают внутрь `compute_service.yaml` под schema key `seaf.company.ta.services.compute_services`, то есть тип сущности и контейнер YAML расходятся.
- [x] Заполнять обязательные поля по SEAF-схеме или явно маркировать YAML как невалидный черновик. На свежем output отсутствуют:
  - `model` и `realization_type` у `438/438` `network_component`,
  - `availabilityzone` у `40/40` `compute_service`,
  - `technology` у `3/3` `kb`,
  - `availabilityzone` у `7/7` `cluster_virtualization`.
- [x] Расширить `ManualDrawioValidator` на проверку этих обязательных полей. Сейчас он проверяет `service_type` только для `compute_service`, но не проверяет `model`/`realization_type` для компонентов, `availabilityzone` для compute/cluster и `technology` для `kb`, поэтому структурно неполный YAML не отлавливается.

### P1 — качество иерархии и классификации
- [x] Добить восстановление связей не только для `network_component`, но и для сервисных сущностей. На свежем output без `network_connection` остаются `39/40` `compute_service`, `3/3` `kb`, `6/7` `storages`, `6/7` `cluster_virtualization`.
- [x] Проверить разбор внешнего контура. `Internet`, `Leased Lines`, `Партнер`, `Биржа`, `Регулятор`, `Сеть Сбербанка` всё ещё лежат в `network_segment.yaml` без `location` и лишь с `external: true`; при этом внутренние объекты иногда привязываются к `segment: project.network_segment.internet` при `location` внутри ЦОДа, что смешивает внешнюю и внутреннюю модели.
- [x] Убрать остаточные `unknown` и template/noise-объекты из `network_component.yaml`: остаются `42` `unknown`, включая `Clients/Guests Access to Intrernet`, `Provider доставки OTР`, `VoIP / Telecom Provider`, `OF-Internet-edge`, `OF-NT-WAN-edge`, `Mitigation`, `ВКС`, `iOT`, `SaaS Provider/Сервис`, `СБЕР`, `ДКА`, `ДКБ`.
- [x] Уточнить mapping пользовательских устройств: сейчас `Проводные подключения АРМ Сотрудников` и `АРМ Администраторов` попадают в `seaf.company.ta.components.networks` как `type: user_device`, хотя в SEAF для этого есть отдельная сущность `seaf.company.ta.components.user_devices`.
- [x] Восстановить нормализацию шума для `+wIPS`: элемент всё ещё попадает в `network_component.yaml` как `security`, хотя по смыслу это скорее маркер/бейдж рядом с устройством, а не самостоятельная сущность.

### P2 — контроль соответствия целевой SEAF-модели
- [x] Проверить enum-совместимость значений `type` у `network_component`: mapper пишет `server`, `firewall`, `balancer`, `ap`, `security`, `user_device`, а в `seaf.company.ta.components.networks.type` ожидаются русские enum-значения (`Маршрутизатор`, `Контроллер WiFi`, `МСЭ`, `Криптошлюз`, `VPN`, `NAT`, `Коммутатор`).
- [x] Проверить enum-совместимость `service_type` у `compute_service`: сейчас пишется технический ярлык `infrastructure` / `backup`, а в схеме `seaf.company.ta.services.compute_services.service_type` ожидаются конкретные русские значения из enum.
- [x] Добавить в `summary_report.md` отдельную метрику по покрытию `network_connection` для сервисов и отдельную выборку “объекты во внешнем сегменте при внутренней локации”.

---

## Замечания по промежуточной проверке выполнения backlog

### Что реально улучшилось
- [x] Базовая структура `3 локации -> сегменты -> сети/устройства/сервисы` стала читаться лучше: на свежем прогоне извлекаются 3 площадки, 25 сегментов, 90 сетей, 340 сетевых компонентов, 36 compute-сервисов, 3 KB, 7 storage, 7 cluster, 4 backup.
- [x] `location` у `network`, `network_component` и сервисных сущностей теперь пишется массивом, `storage.yaml` вынесен в `seaf.company.ta.services.storages`, `backup.yaml` создаётся отдельно.
- [x] Доля `unknown` для `network_component` действительно снижена до `30/340 = 8.8%`, то есть формальный P1-порог по неизвестным типам выполнен.

### P0 — замечания по качеству, которые ещё нужно проработать
- [x] Убрать ложноположительный зелёный статус валидатора. На свежем output `ManualDrawioValidator` пишет `✅ Валидация YAML пройдена успешно`, но при этом не проверяет enum-совместимость `network_component.type`, `compute_service.service_type`, `kb.technology` и обязательные поля `backup.availabilityzone` / `backup.path`, поэтому семантически невалидный YAML проходит как успешный.
- [x] Привести `network_component.type` к enum из `seaf.company.ta.components.networks`. Сейчас `116/340` сетевых компонентов имеют значения вне схемы, в том числе `Межсетевой экран (файрвол)`, `Балансировщик нагрузки`, `unknown`; в схеме допустимы `МСЭ`, `Криптошлюз`, `VPN`, `NAT`, `Коммутатор`, `Маршрутизатор`, `Контроллер WiFi`.
- [x] Исправить `compute_service.service_type`: сейчас у `36/36` сервисов стоит `Серверы приложений и т.д.` с кириллической `С`, а в `data/seaf_schema.yaml` enum содержит `Cерверы приложений и т.д.` с латинской `C`; из-за этого все compute-сервисы формально вне enum.
- [x] Исправить `kb.technology`: у `3/3` объектов `BitBucket`, `Jira`, `Confluence` пишется `Неизвестно`, но такого значения нет в enum `seaf.company.ta.services.kb.technology`.
- [x] Дозаполнить `backup.yaml` до схемы `seaf.company.ta.services.backups`: у `4/4` backup-объектов нет `availabilityzone` и `path`, хотя оба поля обязательны.

### P1 — замечания по иерархии и связям
- [x] Довести восстановление `network_connection` для сервисов. Сейчас без связей остаются `32/36` compute-сервисов, `3/3` KB, `4/7` storage; для сетевых компонентов без связей `143/340 = 42.1%`, то есть задача блока 14 ещё не закрыта по смыслу, даже если формально порог `>80%` пройден.
- [x] Разобрать смешение внешних сегментов и внутренних локаций. В `summary_report.md` остаётся 14 объектов с `parent_segment.is_external = true` при внутренней `location`, например `INT-Backup&Recovery`, `DMZ-CORE`, `CNTXT4/NGFW3(4)`, `2FA (OTP/Token/SMS)`, `Router 1,2`.
- [x] Развести `user_device` / `server` как отдельные SEAF-сущности или явно исключать их из контура v0.3. Сейчас `NON_NETWORK_COMPONENTS` складывает их в `self.user_devices` / `self.servers`, но `ManualDrawioMapper.map_all()` эти коллекции вообще не маппит, то есть такие объекты молча теряются.
- [x] Убрать остаточные `unknown`-компоненты, которые уже можно типизировать правилами или вынести из сетевых устройств: `Интернет узел связи DDOS ARBOR TMS`, `МСЭ SP EDGE/vRouter`, `Web-site / Landing page`, `Администраторы`, `Подрядчики`, `СКУД`, `Видеонаблюдение`, `Vuln scan`, `2FA (OTP/Token/SMS)`.

### P2 — замечания по backlog-статусу и отчётности
- [x] Не держать `v0.3.1` в статусе `DONE`, пока пункты выше не закрыты или явно не перенесены в `v0.4` с объяснением критерия приёмки. Сейчас статус `DONE` вверху файла противоречит фактическим результатам проверки.
- [x] Синхронизировать версию отчёта: заголовок `summary_report.md` уже `v0.3.1`, но футер всё ещё `*Отчёт v0.3 сгенерирован автоматически*`.

---

## v0.3.2 — Доработка валидности YAML и качества связей (DONE)

### P0 — SEAF-валидность и честная валидация
- [x] Расширить `ManualDrawioValidator` проверкой enum-значений по `data/seaf_schema.yaml` для `network_component.type`, `network_component.realization_type`, `compute_service.service_type`, `kb.technology`.
- [x] Добавить в `ManualDrawioValidator` проверку обязательных полей `backup.availabilityzone` и `backup.path`, а также ссылочную проверку `network_connection` на существующие OID сетей.
- [x] Исправить маппинг `network_component.type`: привести значения к допустимому enum SEAF (`МСЭ`, `Криптошлюз`, `VPN`, `NAT`, `Маршрутизатор`, `Контроллер WiFi`, `Коммутатор`) и убрать генерацию `Межсетевой экран (файрвол)`, `Балансировщик нагрузки`, `unknown` без явного `review_needed`.
- [x] Исправить `compute_service.service_type` на точное значение из enum схемы, включая проблему латинской `C` в `Cерверы приложений и т.д.`.
- [x] Исправить `kb.technology`: вместо `Неизвестно` подставлять допустимое enum-значение по правилам классификации или выносить объект в `review_needed`.
- [x] Дозаполнять `backup.yaml` полями `availabilityzone` и `path`; если путь хранения из схемы не извлечён, явно маркировать объект как требующий ручной доработки и не пропускать его как валидный.

### P1 — Иерархия, связи, покрытие сущностей
- [x] Доработать восстановление `network_connection` для `compute_service`, `kb`, `storage`, `backup`, `network_component`; целевой минимум для следующей итерации — не менее 60% объектов каждого типа со связью, либо отдельный список исключений с причиной.
- [x] Реализовать алгоритм привязки линии к ближайшему объекту по кратчайшему расстоянию, а не только по попаданию `sourcePoint` / `targetPoint` в bounding box.
- [x] Разобрать кейсы смешения `external segment + internal location`: не допускать, чтобы внутренние объекты ЦОДа/офиса наследовали `segment` от `Internet`, `Leased Lines`, `Партнер`, `Биржа`, `Регулятор`.
- [x] Определить судьбу `user_devices` и `servers`: либо маппить их в соответствующие SEAF-сущности отдельными YAML, либо исключать из классификации с явным объяснением в отчёте; текущую молчаливую потерю данных убрать.
- [x] Дотипизировать оставшиеся `unknown`-объекты отдельными правилами или перевести их в `review_needed`, чтобы в `network_component.yaml` не оставались бизнес-акторы и сервисные подписи вроде `Администраторы`, `Подрядчики`, `Web-site / Landing page`.

### P2 — Отчётность и критерии закрытия версии
- [x] Снять статус `DONE` с `v0.3.1` или перенести незакрытые пункты в `v0.3.2` с явными acceptance criteria, чтобы backlog не противоречил фактической проверке.
- [x] Синхронизировать версию `summary_report.md`: заголовок и футер должны показывать одну и ту же версию генератора/отчёта.
- [x] Добавить в `summary_report.md` отдельные метрики по `enum violations`, `backup missing required fields`, `service network_connection coverage`, `objects dropped by mapper`.
- [x] Добавить в репозиторий минимальный regression-check для `scripts/manual_drawio_to_seaf.py` на целевой ручной схеме: запуск, проверка наличия 3 локаций, ненулевых сегментов/сетей/компонентов, отсутствие enum violations, отсутствие backup без required fields.

### Acceptance criteria для `v0.3.2`
- [x] `ManualDrawioValidator` не выдаёт зелёный статус при enum-ошибках, битых `network_connection` или отсутствии required-полей `backup`.
- [x] `network_component.type`, `compute_service.service_type`, `kb.technology` соответствуют enum из `data/seaf_schema.yaml`.
- [x] Для `backup.yaml` заполнены `availabilityzone` и `path` либо такие объекты явно вынесены в список ручной доработки и не считаются валидными.
- [x] Для каждой из 3 локаций сохраняется иерархия `location -> segment -> network -> component/service` без смешения внутренних объектов с внешними сегментами.
- [x] Покрытие `network_connection` по сервисам и сетевым компонентам улучшается относительно текущего прогона и отражается в отчёте отдельными метриками.

---

## v0.3.3 — Замечания по проверке после `v0.3.2`

### Что действительно стало лучше
- [x] Enum-значения `network_component.type`, `compute_service.service_type`, `kb.technology` и обязательные поля `backup.availabilityzone/path` в текущем output больше не падают по базовой проверке.
- [x] `user_device.yaml` и `server.yaml` теперь физически генерируются, то есть прежняя молчаливая потеря этих классов объектов частично устранена.
- [x] Покрытие связей у `network_component` стало лучше: на свежем прогоне без `network_connection` осталось `30/120 = 25%`, а не `143/340`.

### P0 — замечания, которые нужно исправить
- [x] Исправить генерацию `server.yaml`: сейчас mapper пишет schema key `seaf.company.ta.components.servers`, но в `data/seaf_schema.yaml` такой сущности нет, то есть файл формально не принадлежит текущему SEAF2-метамоделю. Нужно либо маппить серверы в реально существующую TA-сущность, либо явно исключить `server.yaml` из поставки и описать это в отчёте.
- [x] Довести `user_device.yaml` до схемы `seaf.company.ta.components.user_devices`: у всех объектов отсутствует обязательное поле `device_type`, а у части объектов нет `location` / `segment` (`Удаленные пользователи (корп.)`, `АРМ Сотрудников`, `Администраторы`, `Подрядчики`, `Web-browser`). Это означает, что новая выгрузка user devices пока структурно неполная.
- [x] Расширить `ManualDrawioValidator` на `user_device.yaml` и на новые/дополнительные выходные файлы. Сейчас валидатор проверяет только 11 заранее заданных YAML и вообще не проверяет `user_device.yaml` / `server.yaml`, поэтому не видит отсутствие `device_type` и не ловит несуществующий schema key `seaf.company.ta.components.servers`.

### P1 — замечания по качеству классификации и иерархии
- [x] Разобрать резкий рост `kb` с `3` до `207`. По свежему output в `kb.yaml` попадает множество повторяющихся бейджей `AV`, `EDR`, `DLP`, `SOC`, `Anti DDoS` и т.п.; по смыслу это часто атрибуты/маркировки рядом с устройствами или приложениями, а не самостоятельные KB-сервисы. Нужен отдельный критерий, где такие бейджи превращаются в свойства/связи, а где в самостоятельные `seaf.company.ta.services.kb`.
- [x] Не считать `v0.3.2` закрытым по иерархии внешнего контура: в свежем `summary_report.md` всё ещё `14` объектов находятся во внешнем сегменте при внутренней локации, а в YAML есть прямые примеры `project.compute_service.dc_rented.monitoring_resources -> segment: project.network_segment.internet` и `project.backup.dc_rented.backing_up_and_recovery_system... -> segment: project.network_segment.internet`.
- [x] Довести `network_connection` для сервисных сущностей, а не только для `network_component`: в отчёте всё ещё `125` сервисов без связей, в основном из-за раздутого `kb.yaml`, поэтому формальный зелёный статус не отражает реальное качество service-mapping.

### P2 — замечания по отчётности и regression-тесту
- [x] Синхронизировать версию отчёта в `summary_report.md`: заголовок всё ещё `v0.3.1`, а футер уже `v0.3.2`.
- [x] Усилить `tests/run_drawio_regression.py`: текущий тест проверяет только наличие строки `"zones": 3`, отсутствие `❌ Ошибки валидации` и наличие зелёного сообщения. Он не парсит YAML, не проверяет `user_device/server`, не ловит взрыв `kb=207`, не контролирует `objects in external segment with internal location`, поэтому пропускает существенные регрессии качества.

### Acceptance criteria для `v0.3.3`
- [x] Все генерируемые YAML используют только schema key, реально описанные в `data/seaf_schema.yaml`, либо файл явно исключён из output.
- [x] `user_device.yaml` проходит проверку обязательного `device_type`, а объекты без `location/segment` либо исправлены, либо вынесены в `review_needed`.
- [x] Количество `kb` соответствует ожидаемой семантике схемы и не раздувается за счёт повторяющихся AV/EDR/DLP бейджей без явного правила агрегации/дедупликации.
- [x] Внутренние объекты ЦОД/офиса не получают `segment=Internet/Leased Lines/...`.
- [x] Regression test парсит выходные YAML и проверяет хотя бы schema keys, обязательные поля для `user_device`, отсутствие `server.yaml` с несуществующей схемой, верхнюю границу по `kb` и отсутствие внутренних объектов во внешних сегментах.

---

## v0.3.4 — Замечания по проверке готовности `v0.3.3` (DONE)

### Что стало лучше
- [x] `server.yaml` больше не генерируется, то есть несуществующий schema key `seaf.company.ta.components.servers` убран из output.
- [x] `kb` больше не раздувается до сотен бейджей: на свежем прогоне `kb=35`, а не `207`.
- [x] `user_device.yaml` теперь содержит обязательное поле `device_type`, и regression-test проверяет этот факт.

### P0 — блокеры до принятия `v0.3.3`
- [x] Исправить несоответствие acceptance criteria по `user_device.yaml`: сейчас `ManualDrawioMapper` подставляет `location: ['review_needed']` и `segment: 'review_needed'` для объектов без контекста, а `ManualDrawioValidator` считает такие значения невалидными только частично и не включает `review_needed_fields` в `self.metrics`. В результате свежий output содержит 5 таких `user_device`, но валидатор всё равно пишет `Полей 'review_needed': 0 OK`.
- [x] Дочинить разделение внутреннего и внешнего контура. В свежем output всё ещё есть внутренние сущности с `segment: project.network_segment.internet`, например `project.compute_service.dc_rented.monitoring_resources` и `project.backup.dc_rented.backing_up_and_recovery_system.xq3pkyliy71yueaidazh_1164`, а в `summary_report.md` остаётся `11` объектов во внешнем сегменте при внутренней локации. Это прямо нарушает acceptance criteria `v0.3.3`.
- [x] Усилить `tests/run_drawio_regression.py`, чтобы он падал на `review_needed` в `user_device`, на `segment=project.network_segment.internet` у внутренних сервисов/backup и на ненулевое число объектов “во внешнем сегменте при внутренней локации”. Сейчас тест проходит, хотя эти дефекты воспроизводятся.

### P1 — качество классификации и отчётности
- [x] Синхронизировать версии в `summary_report.md`: заголовок уже `v0.3.3`, но секция `### 🧩 Новые сущности` всё ещё подписана как `v0.3.1`, а футер как `v0.3.2`.
- [x] Разобрать остаточные `kb` без `segment/location`, например `Endpoint Detection & Response (EDR)`, `Security Information and Event Management (SIEM)`, `Anti DDoS`, `Container vulnerability scanner`, `Интернет узел связи DDOS ARBOR TMS`. Сейчас объекты уже не массово дублируются, но часть KB всё ещё выпадает из иерархии `location -> segment`.
- [x] Пересмотреть правило “маленький KB = badge”. Сейчас в `_classify_vertex` оно просто меняет `seaf_type` на `badge` и делает `return`, не помечая объект как `classified`, не добавляя его в `noise` и не отражая это в отчёте. Это создаёт скрытый класс объектов без учёта в метриках и без явного контракта.

### Acceptance criteria для `v0.3.4`
- [x] `ManualDrawioValidator` реально считает `review_needed_fields` и валит quality gate, если такие поля остались в финальном YAML.
- [x] В output нет внутренних `compute_service` / `backup` / `kb` / `network_component` с `segment=project.network_segment.internet` или другим external segment при внутренней локации.
- [x] `tests/run_drawio_regression.py` проверяет `review_needed`, external/internal-segment violations и согласованность версий отчёта.
- [x] Все версии в `summary_report.md` согласованы между заголовком, секциями и футером.
- [x] `badge`-объекты либо явно учитываются в отчёте как noise/ignored, либо маппятся по документированному правилу без скрытой потери.

---

## v0.4 — Финализация и тесты

### Блок 14. Связи (DONE)
- [x] Поднять процент восстановленных связей до 30%+.
- [x] Использовать алгоритм кратчайшего расстояния от линии до объекта.
- [x] **Итог**: Процент связности компонентов вырос до **54.2%** (с начальных 6%).

### Блок 15. Round-trip проверка (DONE)
- [x] Подать результат в `seaf2drawio.py`.
- [x] Получить обратно DrawIO и сравнить составы.
- [x] **Итог**: Статус верификации `Result: GENERATION MATCHES YAML`. Все 22 сегмента и 90 сетей отрисованы.

### Блок 16. Регрессия (DONE)
- [x] Сделать минимальный набор тестов.
- [x] **Итог**: Создан `tests/run_drawio_regression.py`, проверяющий Quality Gates на уровне YAML и логов отрисовки.

---

## v0.4.0 — Детальный отчет по изменениям

### Реализованные улучшения:
1. **Совместимость с `seaf2drawio.py`**:
   - Авто-генерация `Region` и `Availability Zone` в маппере для построения дерева страниц.
   - Прямая привязка площадок к созданным корням.
2. **Восстановление Edge-сетей**:
   - Синхронизация OID с системными паттернами: использование префикса `network.wan.isp.` для внешних сетей.
   - Отрисовка `OF-Internet-edge` и `OF-NT-WAN-edge` на странице Офиса.
3. **Классификация сегментов**:
   - Внедрен **Геометрический приоритет**: сегменты-контейнеры ищутся раньше текстовых меток.
   - Добавлена **HTML-нормализация** имен сегментов (очистка от `<b>`, `<div>`).
   - Расширена цветовая палитра (`#D8D8D8`, `#CCCCCC`) для серых зон.
4. **Чистота схемы**:
   - Заголовки (`title`) очищены от контекста локаций/сегментов в скобках.
5. **Связи**:
   - Роутеры в Офисе и ЦОДах корректно находят свои Edge-сети.

---

## Технический долг (Technical Debt)

1. **Версия Python**: Оригинальный `seaf2drawio.py` требует Python 3.10+ (`match-case`). В текущем окружении (3.9) приходится использовать временные патчи.
2. **Хрупкость ID**: Отрисовка сильно завязана на формат OID (регулярки в `main.yaml`). Изменение схемы именования в маппере ломает отрисовку.
3. **Дедупликация**: Алгоритм склеивания сегментов по типу и локации может ошибочно объединять разные физические боксы одного типа.
4. **Монолитность YAML**: Для round-trip используется `seaf_full.yaml`. Нужно доработать поддержку распределенной структуры файлов через `imports` в `_root.yaml`.

