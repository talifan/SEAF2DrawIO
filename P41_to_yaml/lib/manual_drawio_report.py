class ManualDrawioReport:
    REPORT_VERSION = "v0.3.3"

    def __init__(self, classifier, mapper):
        self.classifier = classifier
        self.mapper = mapper

    def generate_markdown(self):
        report = self.classifier.get_report()
        all_objects = self.classifier.zones + self.classifier.segments + self.classifier.networks + \
                      self.classifier.components + self.classifier.services + self.classifier.kbs + \
                      self.classifier.storages + self.classifier.clusters + self.classifier.k8s_clusters + \
                      getattr(self.classifier, 'backups', [])
        
        md = f"# Отчёт о распознавании ручной DrawIO-схемы ({self.REPORT_VERSION})\n\n"
        
        md += "## Сводка качества\n\n"
        total = len(all_objects)
        no_location = [o for o in all_objects if not o.get('parent_location_id')]
        no_segment = [o for o in all_objects if o.get('seaf_type') in ['network', 'network_component', 'compute_service'] and not o.get('parent_segment_id')]
        no_connections = [o for o in self.classifier.components if not self.classifier.adj.get(o['id']) and not o.get('parent_network_id')]
        unknown_type = [o for o in self.classifier.components if not o.get('component_subtype') or o.get('component_subtype') == 'unknown']
        
        services = self.classifier.services + self.classifier.kbs + self.classifier.storages + self.classifier.clusters + self.classifier.k8s_clusters + getattr(self.classifier, 'backups', [])
        service_no_connections = [o for o in services if not self.classifier.adj.get(o['id']) and not o.get('parent_network_id')]
        
        ext_seg_int_loc = []
        for o in all_objects:
            s_id = o.get('parent_segment_id')
            l_type = o.get('parent_location_type')
            if s_id and l_type in ['dc', 'dc_office']:
                s_cell = next((c for c in self.classifier.cells if c['id'] == s_id), None)
                if s_cell and s_cell.get('is_external'):
                    ext_seg_int_loc.append(o)
        
        md += f"- **Всего объектов:** {total}\n"
        md += f"- **Без локации:** {len(no_location)} ({len(no_location)/total*100:.1f}%)\n" if total else ""
        md += f"- **Без сегмента:** {len(no_segment)}\n"
        md += f"- **Компоненты без связей:** {len(no_connections)}\n"
        md += f"- **Сервисы без связей:** {len(service_no_connections)}\n"
        md += f"- **Неизвестный тип:** {len(unknown_type)}\n"
        md += f"- **Объекты во внешнем сегменте при внутр. локации:** {len(ext_seg_int_loc)}\n\n"
        
        if ext_seg_int_loc:
            md += "### ⚠️ Объекты во внешнем сегменте с внутр. локацией\n"
            for o in ext_seg_int_loc[:10]:
                md += f"- {o.get('value', '---')} (Локация: {o.get('parent_location_value', '---')})\n"
            md += "\n"
        
        md += f"### 🧩 Новые сущности ({self.REPORT_VERSION})\n"
        md += f"- **Инфраструктурные сервисы:** {len(self.classifier.services)}\n"
        md += f"- **Резервное копирование:** {len(getattr(self.classifier, 'backups', []))}\n"
        md += f"- **Базы знаний/DevOps:** {len(self.classifier.kbs)}\n"
        md += f"- **Хранилища:** {len(self.classifier.storages)}\n"
        md += f"- **Кластеры виртуализации:** {len(self.classifier.clusters)}\n"
        md += f"- **Kubernetes:** {len(self.classifier.k8s_clusters)}\n\n"
        md += f"- **Бейджи/лейблы пропущены как noise:** {report.get('badges', 0)}\n\n"

        md += "## Площадки (DC/Office)\n\n"
        for z in self.classifier.zones:
            md += f"- **{z.get('value', '---')}** ({z.get('seaf_type')}) -> `{z.get('seaf_oid')}`\n"
        md += "\n"
        
        md += "## Сервисы и Кластеры (Топ 15)\n\n"
        md += "| Название | Тип SEAF | Локация | Сегмент |\n"
        md += "| --- | --- | --- | --- |\n"
        for s in sorted(services, key=lambda x: x.get('confidence', 0), reverse=True)[:15]:
            md += f"| {s.get('value', '---')} | {s.get('seaf_type')} | {s.get('parent_location_value', '---')} | {s.get('parent_segment_value', '---')} |\n"
        md += "\n"

        md += "## Сетевые сегменты (Топ 15)\n\n"
        md += "| Название | Локация | Тип |\n"
        md += "| --- | --- | --- |\n"
        for s in self.classifier.segments[:15]:
            md += f"| {s.get('value', '---')} | {s.get('parent_location_value', '---')} | {s.get('segment_type', '---')} |\n"
        md += "\n"
        
        md += "## Сети (Топ 15)\n\n"
        md += "| Название | Сегмент | CIDR | VLAN |\n"
        md += "| --- | --- | --- | --- |\n"
        for n in self.classifier.networks[:15]:
            details = n.get('network_details', {})
            md += f"| {n.get('value', '---')} | {n.get('parent_segment_value', '---')} | {details.get('cidr', '---')} | {details.get('vlan', '---')} |\n"
        
        md += f"\n\n---\n*Отчёт {self.REPORT_VERSION} сгенерирован автоматически*"
        
        return md

    def save(self, output_path):
        md = self.generate_markdown()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)
