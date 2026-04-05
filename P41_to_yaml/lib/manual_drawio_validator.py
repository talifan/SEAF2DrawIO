import yaml
import re
import os

class ManualDrawioValidator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.errors = []
        self.metrics = {}
        self.data = {}

    def validate(self):
        self.errors = []
        files = {
            'region': ('dc_region.yaml', 'seaf.company.ta.services.dc_regions'),
            'az': ('dc_az.yaml', 'seaf.company.ta.services.dc_azs'),
            'dc': ('dc.yaml', 'seaf.company.ta.services.dcs'),
            'office': ('dc_office.yaml', 'seaf.company.ta.services.dc_offices'),
            'segment': ('network_segment.yaml', 'seaf.company.ta.services.network_segments'),
            'network': ('network.yaml', 'seaf.company.ta.services.networks'),
            'component': ('network_component.yaml', 'seaf.company.ta.components.networks'),
            'service': ('compute_service.yaml', 'seaf.company.ta.services.compute_services'),
            'kb': ('kb.yaml', 'seaf.company.ta.services.kb'),
            'storage': ('storage.yaml', 'seaf.company.ta.services.storages'),
            'cluster': ('cluster_virtualization.yaml', 'seaf.company.ta.services.cluster_virtualizations'),
            'k8s': ('k8s.yaml', 'seaf.company.ta.services.k8s'),
            'backup': ('backup.yaml', 'seaf.company.ta.services.backups'),
            'user_device': ('user_device.yaml', 'seaf.company.ta.components.user_devices')
        }
        
        all_oids = set()
        network_oids = set()
        location_oids = set()
        segment_oids = set()
        counts = {'total': 0, 'no_location': 0, 'no_segment': 0, 'no_connection': 0, 'unknown_type': 0, 'enum_violations': 0, 'backup_missing_fields': 0, 'review_needed_fields': 0}
        
        # Patterns compatible ENUMs
        nc_types = ['Маршрутизатор (роутер)', 'Точка доступа (Wi-Fi)', 'Межсетевой экран (файрвол)', 'Криптошлюз', 'VPN', 'NAT', 'Коммутатор', 'Балансировщик нагрузки (Load Balancer)']
        nc_reals = ['Виртуальный', 'Физический']
        cs_types = ['Управление ИТ-службой, ИТ-инфраструктурой и ИТ-активами (CMDB, ITSM и т.д.)', 'Управление и автоматизацией (Ansible, Terraform, Jenkins и т.д.)', 'Управление разработкой и хранения кода (Gitlab, Jira и т.д.)', 'Управление сетевым адресным пространством (DHCP, DNS и т.д.)', 'Виртуализация рабочих мест (ВАРМ и VDI)', 'Шлюз, Балансировщик, прокси', 'СУБД', 'Распределенный кэш', 'Интеграционная шина  (MQ, ETL, API)', 'Брокеры сообщений', 'Серверы приложений и т.д.', 'Шлюз API', 'Системы AI/ML', 'Платформы обработки больших данных', 'Файловый ресурс (FTP, NFS, SMB, S3 и т.д.)', 'Коммуникации (АТС, Почта, мессенджеры, СМС шлюзы и т.д.)', 'Управление конечными устройствами (мобильными устройствами)']
        kb_techs = ['Механизмы ААА', 'Межсетевое экранирование', 'Сигнатурный анализ режим обнаружнения вторжений', 'Сигнатурный анализ режим предотвращения вторжений', 'Поведенческий анализ сетевого трафика', 'Динамический анализ угроз Sandbox', 'Защита от атака типа "Отказ в обслуживании"', 'Шифрование канала', 'Потоковый антивирус', 'Управление доступом пользователей', 'Контроль подключений к сети', 'Защита веб-приложений WAF', 'Контентная фильтрация и разграничение доступа в Интернет', 'Шлюзы безопасности прикладного уровня', 'Инструментальный контроль защищенности', 'Безопасность конфигураций', 'Аудит событий КБ']
        ud_types = ['АРМ', 'Терминалы сбора данных (ТСД)', 'Мобильные рабочие места (МРМ)', 'IoT']

        for key, (filename, expected_key) in files.items():
            path = os.path.join(self.output_dir, filename)
            if not os.path.exists(path): continue
            
            with open(path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                if not content: continue
                
                schema_key = list(content.keys())[0]
                if schema_key != expected_key:
                    self.errors.append(f"Wrong schema key in {filename}: expected {expected_key}, found {schema_key}")
                
                objects = content[schema_key]
                self.data[schema_key] = objects
                
                for oid, obj in objects.items():
                    counts['total'] += 1
                    if oid in all_oids: self.errors.append(f"Duplicate OID: {oid}")
                    all_oids.add(oid)
                    
                    if key in ['dc', 'office', 'region']: location_oids.add(oid)
                    if key == 'segment': segment_oids.add(oid)
                    if key == 'network': network_oids.add(oid)
                    
                    loc = obj.get('location')
                    if not loc and not (key == 'segment' and obj.get('external')) and key not in ['region', 'az']:
                        counts['no_location'] += 1
                    
                    if key in ['network', 'component', 'service', 'kb', 'storage', 'user_device']:
                        if not obj.get('segment'): counts['no_segment'] += 1
                        elif obj.get('segment') == 'review_needed': counts['review_needed_fields'] += 1
                        if loc and (loc == 'review_needed' or (isinstance(loc, list) and 'review_needed' in loc)):
                            counts['review_needed_fields'] += 1
                            
                    if key == 'user_device':
                        dtype = obj.get('device_type')
                        if not dtype: self.errors.append(f"Missing mandatory 'device_type' in {oid}")
                        elif dtype not in ud_types:
                            self.errors.append(f"Enum violation 'device_type' in {oid}: {dtype}")
                            counts['enum_violations'] += 1
                    
                    if key == 'component':
                        ctype = obj.get('type')
                        if not obj.get('network_connection'): counts['no_connection'] += 1
                        if ctype == 'unknown' or ctype == 'review_needed': counts['unknown_type'] += 1
                        if ctype not in nc_types:
                            self.errors.append(f"Enum violation 'type' in {oid}: {ctype}")
                            counts['enum_violations'] += 1
                        if 'model' not in obj: self.errors.append(f"Missing mandatory 'model' in {oid}")
                        creal = obj.get('realization_type')
                        if creal not in nc_reals:
                            self.errors.append(f"Enum violation 'realization_type' in {oid}: {creal}")
                            counts['enum_violations'] += 1
                    
                    if key == 'service':
                        stype = obj.get('service_type')
                        if not stype: self.errors.append(f"Missing mandatory 'service_type' in {oid}")
                        elif stype not in cs_types:
                            self.errors.append(f"Enum violation 'service_type' in {oid}: {stype}")
                            counts['enum_violations'] += 1
                        if 'availabilityzone' not in obj: self.errors.append(f"Missing mandatory 'availabilityzone' in {oid}")
                    
                    if key == 'cluster':
                        if 'availabilityzone' not in obj: self.errors.append(f"Missing mandatory 'availabilityzone' in {oid}")
                        
                    if key == 'kb':
                        tech = obj.get('technology')
                        if not tech: self.errors.append(f"Missing mandatory 'technology' in {oid}")
                        elif tech not in kb_techs:
                            self.errors.append(f"Enum violation 'technology' in {oid}: {tech}")
                            counts['enum_violations'] += 1
                            
                    if key == 'backup':
                        if not obj.get('availabilityzone'): counts['backup_missing_fields'] += 1
                        if not obj.get('path'): counts['backup_missing_fields'] += 1

        # Cross-reference validation
        for schema_key, objects in self.data.items():
            for oid, obj in objects.items():
                loc = obj.get('location')
                if loc:
                    for l in (loc if isinstance(loc, list) else [loc]):
                        if l != 'review_needed' and l not in location_oids and l not in all_oids: 
                            self.errors.append(f"Broken location link in {oid}: {l}")
                seg = obj.get('segment')
                if seg:
                    for s in (seg if isinstance(seg, list) else [seg]):
                        if s != 'review_needed' and s not in segment_oids: self.errors.append(f"Broken segment link in {oid}: {s}")
                nconn = obj.get('network_connection')
                if nconn:
                    for nc in (nconn if isinstance(nconn, list) else [nconn]):
                        if nc != 'review_needed' and nc not in network_oids and nc not in all_oids:
                            self.errors.append(f"Broken network_connection link in {oid}: {nc}")

        if counts['total'] > 0:
            self.metrics = {
                'no_location_pct': (counts['no_location'] / counts['total']) * 100,
                'no_connection_pct': (counts['no_connection'] / max(1, len(self.data.get('seaf.company.ta.components.networks', {})))) * 100,
                'unknown_type_pct': (counts['unknown_type'] / max(1, len(self.data.get('seaf.company.ta.components.networks', {})))) * 100,
                'enum_violations': counts['enum_violations'],
                'backup_missing_fields': counts['backup_missing_fields'],
                'review_needed_fields': counts['review_needed_fields']
            }
        return self.errors

    def get_report(self):
        res = ""
        if self.errors:
            res += "❌ Ошибки валидации (OID/Ссылки/Типы):\n"
            for e in self.errors[:10]: res += f"  - {e}\n"
        gate_failures = []
        if self.metrics:
            if self.metrics['no_location_pct'] > 20: gate_failures.append("Слишком много объектов без локации")
            if self.metrics['no_connection_pct'] > 80: gate_failures.append("Слишком много компонентов без связей")
            if self.metrics['unknown_type_pct'] > 20: gate_failures.append("Слишком много неизвестных типов")
            if self.metrics.get('enum_violations', 0) > 0: gate_failures.append("Найдены ошибки в ENUM значениях")
        if not self.errors and not gate_failures: res += "✅ Валидация YAML пройдена успешно (OID, Ссылки, Качество, Типы).\n"
        elif not self.errors: res += "⚠️ Структурная валидация пройдена, но Quality Gates НЕ выполнены.\n"
        else: res += "❌ Валидация НЕ пройдена.\n"
        if self.metrics:
            res += f"\n📊 Quality Gates (v0.3.3):\n  - Объектов без локации: {self.metrics['no_location_pct']:.1f}% {'OK' if self.metrics['no_location_pct'] <= 20 else '❌'}\n  - Компонентов без связей: {self.metrics['no_connection_pct']:.1f}% {'OK' if self.metrics['no_connection_pct'] <= 80 else '❌'}\n  - Неизвестных типов: {self.metrics['unknown_type_pct']:.1f}% {'OK' if self.metrics['unknown_type_pct'] <= 20 else '❌'}\n  - Ошибок ENUM: {self.metrics.get('enum_violations', 0)} {'OK' if self.metrics.get('enum_violations', 0) == 0 else '❌'}\n  - Ошибок Backup: {self.metrics.get('backup_missing_fields', 0)} {'OK' if self.metrics.get('backup_missing_fields', 0) == 0 else '❌'}\n  - Полей 'review_needed': {self.metrics.get('review_needed_fields', 0)} {'OK' if self.metrics.get('review_needed_fields', 0) == 0 else '❌'}\n"
        return res
