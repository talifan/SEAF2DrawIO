import re

class ManualDrawioClassifier:
    RULES = {
        'locations': { 'anchors': ['офис дзо', 'цод дзо'] },
        'segments': {
            'DMZ': {'colors': ['#DDD7E6'], 'keywords': ['dmz']},
            'INT-NET': {'colors': ['#FFCE9F', '#FFF2CC', '#FFE6CC'], 'keywords': ['внутренняя сеть', 'vlan prod', 'vnutrennyaya set', 'int-net']},
            'INT-SECURITY-NET': {'colors': ['#B7DEE8', '#DAE8FC'], 'keywords': ['защищенный сегмент', 'zashchishchennyy segment', 'security net']},
            'INET-EDGE': {'colors': ['#BFBFBF', '#D8D8D8', '#CCCCCC'], 'keywords': ['inet-edge', 'internet edge', 'inet edge']},
            'EXT-WAN-EDGE': {'colors': ['#BFBFBF', '#D8D8D8', '#CCCCCC'], 'keywords': ['ext wan-edge', 'wan edge', 'ext-wan', 'ext wan']},
            'INT-WAN-EDGE': {'colors': ['#BFBFBF', '#D8D8D8', '#CCCCCC'], 'keywords': ['int wan-edge', 'int-wan', 'int wan']},
            'INTERNET': {'colors': ['#FDEBDD'], 'keywords': ['internet', 'интернет']},
            'TRANSPORT-WAN': {'colors': ['#FFCC66'], 'keywords': ['транспортная сеть', 'wan', 'leased lines', 'transport']},
        },
        'external': ['internet', 'партнер', 'биржа', 'регулятор', 'сеть сбербанка', 'провайдер']
    }

    ENTITY_RULES = [
        ('k8s', ['k8s', 'kubernetes'], {'technology': 'kubernetes'}),
        ('cluster_virtualization', ['esxi cluster', 'hyper-v cluster', 'виртуализация', 'cluster'], {'hypervisor': 'esxi', 'availabilityzone': ['project.dc_az.auto_created']}),
        ('compute_service', ['confluence', 'wiki', 'knowledge base', 'база знаний', 'bitbucket', 'jira'], {'service_type': 'Управление разработкой и хранения кода (Gitlab, Jira и т.д.)', 'availabilityzone': ['project.dc_az.auto_created']}),
        ('storage', ['storage', 'хранилище', 's3', 'ceph', 'san', 'nas', 'netapp', 'emc'], {'storage_type': 'block'}),
        ('compute_service', ['dns', 'dhcp', 'active directory', 'ad dc', 'ntp', 'mail server', 'email', 'exchange', 'jenkins', 'ansible', 'zabbix', 'nagios', 'syslog', 'radius', 'pam', 'monitoring'], {'service_type': 'Серверы приложений и т.д.', 'availabilityzone': ['project.dc_az.auto_created']}),
        ('compute_service', ['balancer', 'f5', 'citrix', 'lb', 'big-ip'], {'service_type': 'Шлюз, Балансировщик, прокси', 'availabilityzone': ['project.dc_az.auto_created']}),
        ('kb', ['soc', 'siem', 'edr'], {'technology': 'Аудит событий КБ'}),
        ('kb', ['dlp', 'antivirus', 'av'], {'technology': 'Потоковый антивирус'}),
        ('kb', ['sandbox', 'fireeye'], {'technology': 'Динамический анализ угроз Sandbox'}),
        ('kb', ['waf'], {'technology': 'Защита веб-приложений WAF'}),
        ('kb', ['2fa', 'otp', 'token', 'sms'], {'technology': 'Механизмы ААА'}),
        ('kb', ['vuln scan', 'scanner', 'db securiry', 'db security'], {'technology': 'Инструментальный контроль защищенности'}),
        ('kb', ['ips', 'ids'], {'technology': 'Сигнатурный анализ режим предотвращения вторжений'}),
        ('kb', ['anti ddos', 'arbor tms', 'ddos'], {'technology': 'Защита от атака типа "Отказ в обслуживании"'}),
        ('backup', ['backup', 'recovery', 'резервное копирование'], {'service_type': 'backup', 'availabilityzone': ['project.dc_az.auto_created'], 'path': '/backup'}),
    ]

    COMPONENT_PRIORITY = [
        ('Криптошлюз', ['mail security', 'security gateway', 'vpn', 'фпсу', 'ipsec']),
        ('Межсетевой экран (файрвол)', ['ngfw', 'firewall', 'межсетевой экран', 'checkpoint', 'fortinet', 'asa', 'fw', 'мсэ', 'ngfw']),
        ('Маршрутизатор (роутер)', ['telecom gate', 'router', 'маршрутизатор', 'роутер', 'asr', 'isr', 'шлюз', 'gate', 'nat']),
        ('Коммутатор', ['switch', 'коммутатор', 'catalyst', 'nexus', 'stack', 'sw']),
        ('Точка доступа (Wi-Fi)', ['access point', 'точка доступа', 'wi-fi', 'wifi', 'ap'])
    ]

    NON_NETWORK_COMPONENTS = [
        ('k8s', ['k8s', 'kubernetes', 'cluster', 'master node', 'worker node']),
        ('server', ['app server', 'database', 'it services', 'server', 'сервер', 'node', 'хост', 'esxi', 'vm', 'backend', 'frontend', 'sql']),
        ('storage', ['storage', 'хранилище', 's3', 'ceph', 'netapp', 'emc']),
        ('user_device', ['browser', 'workstation', 'pc', 'арм', 'клиент', 'пользователи', 'администраторы', 'подрядчики'])
    ]

    def __init__(self, cells):
        self.cells = cells
        for i, cell in enumerate(self.cells): cell['z_index'] = i
        self.zones, self.segments, self.networks, self.components, self.links, self.unknown = [], [], [], [], [], []
        self.services, self.kbs, self.storages, self.clusters, self.k8s_clusters, self.backups = [], [], [], [], [], []
        self.user_devices, self.servers, self.badges = [], [], []
        self.noise_keywords = ['x2', 'x items', 'условные обозначения', 'компонент', 'ас', 'автоматизированная система', 'согласовано', 'версия 01', 'сбер', 'сбербанк', 'сеть сбербанка', '+wips', 'clients/guests access to intrernet', 'provider доставки otр', 'voip / telecom provider', 'mitigation', 'вкс', 'iot', 'saas provider/сервис', 'дка', 'дкб', 'корпоративные клиенты', 'удаленные пользователи', 'web-site', 'landing page', 'скуд', 'видеонаблюдение', 'клиенты', 'guests', 'provider']

    def classify_all(self):
        self._find_major_locations()
        # P0 Fix: Find segments FIRST so they are not misclassified as networks/labels
        self._find_segments()
        for cell in self.cells:
            if cell.get('classified'): continue
            if cell.get('edge'):
                cell['seaf_type'] = 'network_link'; cell['classified'] = True; self.links.append(cell)
            elif cell.get('vertex'):
                self._classify_vertex(cell)
        self._assign_spatial_parents_improved()
        self._identify_external_segments()
        self._resolve_duplicates_advanced()
        self._build_adjacency_advanced()

    def _get_fill_color(self, cell):
        style = cell.get('style', '')
        match = re.search(r'fillColor=([^;]+)', style)
        return match.group(1).upper() if match else 'NONE'

    def _find_major_locations(self):
        anchors = []
        for cell in self.cells:
            if not cell.get('vertex'): continue
            val = cell.get('value', '').lower()
            if any(k in val for k in self.RULES['locations']['anchors']): anchors.append(cell)
        for anchor in anchors:
            l_name = anchor['value'].lower()
            l_type = 'dc_office' if 'офис' in l_name else 'dc'
            l_suffix = 'office' if 'офис' in l_name else ('dc_cloud' if 'облачный' in l_name else 'dc_rented')
            giant_container, max_area = None, 0
            lg = anchor['geometry']; ax, ay = anchor.get('abs_x', lg['x']), anchor.get('abs_y', lg['y'])
            for cell in self.cells:
                if not cell.get('vertex') or cell['id'] == anchor['id']: continue
                cg = cell.get('geometry')
                if not cg or cg.get('width', 0) < 1000: continue
                cax, cay = cell.get('abs_x', cg['x']), cell.get('abs_y', cg['y'])
                if (cax - 100 <= ax <= cax + cg['width'] + 100 and cay - 100 <= ay <= cay + cg['height'] + 100):
                    area = cg['width'] * cg['height']
                    if area > max_area: max_area = area; giant_container = cell
            target = giant_container if giant_container else anchor
            if not target.get('classified') or target.get('seaf_type') != l_type:
                target['seaf_type'] = l_type; target['classified'] = True; target['value'] = anchor['value']
                target['location_suffix'] = l_suffix; target['confidence'] = 1.0; self.zones.append(target)
                if giant_container: anchor['is_noise'] = True; anchor['classified'] = True

    def _identify_external_segments(self):
        for s in self.segments:
            if not s.get('parent_location_id'):
                s['is_external'] = True

    def _find_segments(self):
        for cell in self.cells:
            if not cell.get('vertex') or cell.get('classified'): continue
            geom = cell.get('geometry')
            # Segments are large containers
            if not geom or geom.get('width', 0) < 150: continue
            
            # Clean HTML tags and normalize text
            val = re.sub(r'<[^>]*>', ' ', cell.get('value', '')).strip()
            val_lower = val.lower()
            color = self._get_fill_color(cell)
            
            is_seg, seg_type = False, 'unknown'
            for s_type, rules in self.RULES['segments'].items():
                match_color = color in rules.get('colors', [])
                match_keyword = rules.get('keywords') and any(k in val_lower for k in rules['keywords'])
                
                # Gray boxes require keyword match to be a segment
                if color in ['#BFBFBF', '#D8D8D8', '#CCCCCC']:
                    if match_keyword:
                        is_seg = True; seg_type = s_type; break
                elif match_color or match_keyword:
                    is_seg = True; seg_type = s_type; break
            
            if is_seg:
                cell['seaf_type'] = 'network_segment'; cell['segment_type'] = seg_type; cell['classified'] = True; cell['confidence'] = 0.85; self.segments.append(cell)

    def _classify_vertex(self, cell):
        val = cell.get('value', ''); val_clean = re.sub(r'\s+', ' ', val).strip(); val_lower = val_clean.lower()
        if val_lower in self.noise_keywords or len(val_clean) <= 1:
            cell['is_noise'] = True; cell['classified'] = True; return
        cidr_p, vlan_p = r'(\d+\.\d+\.\d+\.\d+|x+\.x+\.x+\.x+)\s*/\s*(\d+|x+)', r'(vlan|влан|lan)\s*(\d+|x+)'
        if re.search(cidr_p, val_lower) or re.search(vlan_p, val_lower) or any(k in val_lower for k in ['internet-edge', 'wan-edge']):
            cm, vm = re.search(cidr_p, val_lower), re.search(vlan_p, val_lower)
            cell['seaf_type'] = 'network'; cell['classified'] = True; cell['confidence'] = 0.98
            cell['network_details'] = {'cidr': cm.group(0) if cm else None, 'vlan': vm.group(2) if vm else None}
            if 'x' in val_lower or not (cm or vm): cell['is_placeholder'] = True
            self.networks.append(cell); return
        for stype, keywords, fields in self.ENTITY_RULES:
            for k in keywords:
                if re.search(rf'(\b|/){re.escape(k)}(\b|/)', val_lower):
                    cell['seaf_type'] = stype; cell['classified'] = True; cell['confidence'] = 0.95; cell['entity_fields'] = fields
                    geom = cell.get('geometry', {})
                    if stype == 'kb' and geom.get('width', 0) < 45 and geom.get('height', 0) < 45:
                        cell['seaf_type'] = 'badge'; self.badges.append(cell)
                        return
                    if stype == 'compute_service': self.services.append(cell)
                    elif stype == 'kb': self.kbs.append(cell)
                    elif stype == 'storage': self.storages.append(cell)
                    elif stype == 'cluster_virtualization': self.clusters.append(cell)
                    elif stype == 'k8s': self.k8s_clusters.append(cell)
                    elif stype == 'backup': self.backups.append(cell)
                    return
        for stype, keywords in self.NON_NETWORK_COMPONENTS:
            for k in keywords:
                p = rf'({re.escape(k)})' if len(k) < 5 else rf'(\b|/){re.escape(k)}(\b|/)'
                if re.search(p, val_lower):
                    cell['seaf_type'] = 'non_network_component'; cell['component_subtype'] = stype; cell['classified'] = True; cell['confidence'] = 0.95
                    if stype == 'user_device': self.user_devices.append(cell)
                    elif stype == 'server': self.servers.append(cell)
                    elif stype == 'storage': self.storages.append(cell)
                    elif stype == 'k8s': self.k8s_clusters.append(cell)
                    return
        for stype, keywords in self.COMPONENT_PRIORITY:
            for k in keywords:
                p = rf'({re.escape(k)})' if len(k) < 5 else rf'(\b|/){re.escape(k)}(\b|/)'
                if re.search(p, val_lower):
                    cell['seaf_type'] = 'network_component'; cell['component_subtype'] = stype; cell['classified'] = True; cell['confidence'] = 0.95; self.components.append(cell); return
        self.unknown.append(cell)

    def _assign_spatial_parents_improved(self):
        sorted_locs = sorted(self.zones, key=lambda l: l['geometry']['width'] * l['geometry']['height'])
        sorted_segs = sorted(self.segments, key=lambda s: s['geometry']['width'] * s['geometry']['height'])
        sorted_nets = sorted(self.networks, key=lambda n: n['geometry']['width'] * n['geometry']['height'])
        for s in self.segments:
            geom = s['geometry']; ax, ay = s.get('abs_x', geom['x']), s.get('abs_y', geom['y']); cx, cy = ax + geom['width']/2, ay + geom['height']/2
            for loc in sorted_locs:
                if loc['id'] == s['id']: continue
                if self._point_in_box(cx, cy, loc, tol=150):
                    s['parent_location_id'] = loc['id']; s['parent_location_value'] = loc.get('value')
                    s['parent_location_type'] = loc.get('seaf_type'); s['location_suffix'] = loc.get('location_suffix'); break
        for cell in self.cells:
            if not cell.get('vertex') or cell.get('is_noise') or cell.get('seaf_type') in ['dc', 'dc_office', 'network_segment']: continue
            geom = cell.get('geometry'); ax, ay = cell.get('abs_x', geom['x']), cell.get('abs_y', geom['y']); cx, cy = ax + geom['width']/2, ay + geom['height']/2
            for s in sorted_segs:
                if self._point_in_box(cx, cy, s, tol=30):
                    cell['parent_segment_id'] = s['id']; cell['parent_segment_value'] = s.get('value'); break
            if cell.get('parent_segment_id'):
                seg = next((x for x in self.segments if x['id'] == cell['parent_segment_id']), None)
                if seg and seg.get('parent_location_id'):
                    cell['parent_location_id'] = seg['parent_location_id']; cell['parent_location_value'] = seg['parent_location_value']
                    cell['parent_location_type'] = seg['parent_location_type']; cell['location_suffix'] = seg.get('location_suffix')
            if not cell.get('parent_location_id'):
                for loc in sorted_locs:
                    if self._point_in_box(cx, cy, loc, tol=150):
                        cell['parent_location_id'] = loc['id']; cell['parent_location_value'] = loc.get('value')
                        cell['parent_location_type'] = loc.get('seaf_type'); cell['location_suffix'] = loc.get('location_suffix'); break
            if cell.get('seaf_type') not in ['network']:
                for n in sorted_nets:
                    if self._point_in_box(cx, cy, n, tol=30): # Increased tol to 30
                        cell['parent_network_id'] = n['id']; break

    def _resolve_duplicates_advanced(self):
        to_remove = []
        for i, s1 in enumerate(self.segments):
            if s1['id'] in to_remove: continue
            for j in range(i + 1, len(self.segments)):
                s2 = self.segments[j]
                if s2['id'] in to_remove: continue
                # Only merge segments if they are close AND belong to same location
                if s1.get('segment_type') == s2.get('segment_type') and s1.get('parent_location_id') == s2.get('parent_location_id'):
                    g1, g2 = s1['geometry'], s2['geometry']
                    if abs(g1['x'] - g2['x']) < 50 and abs(g1['y'] - g2['y']) < 50:
                        to_remove.append(s2['id'])
        self.segments = [s for s in self.segments if s['id'] not in to_remove]

    def _build_adjacency_advanced(self):
        self.adj = {}
        for edge in self.links:
            geom = edge.get('geometry'); found_ids = set()
            if edge.get('source'): found_ids.add(edge['source'])
            if edge.get('target'): found_ids.add(edge['target'])
            for pt_key in ['sourcePoint', 'targetPoint']:
                if pt_key in geom:
                    target = self._find_cell_at_point(geom[pt_key]['x'], geom[pt_key]['y'], max_dist=80)
                    if target: found_ids.add(target['id'])
            ids = list(found_ids)
            if len(ids) >= 2:
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        u, v = ids[i], ids[j]
                        self.adj.setdefault(u, []).append(v); self.adj.setdefault(v, []).append(u)

    def _point_in_box(self, x, y, cell, tol=0):
        geom = cell.get('geometry'); cx, cy = cell.get('abs_x', geom['x']), cell.get('abs_y', geom['y'])
        return (cx - tol <= x <= cx + geom['width'] + tol and cy - tol <= y <= cy + geom['height'] + tol)

    def _find_cell_at_point(self, x, y, max_dist=150):
        candidates = []
        for cell in self.cells:
            if not cell.get('vertex') or cell.get('is_noise'): continue
            geom = cell.get('geometry'); gx, gy = cell.get('abs_x', geom['x']), cell.get('abs_y', geom['y'])
            dx = max(gx - x, 0, x - (gx + geom.get('width', 0)))
            dy = max(gy - y, 0, y - (gy + geom.get('height', 0)))
            dist = (dx*dx + dy*dy)**0.5
            if dist <= max_dist:
                if cell.get('seaf_type') not in ['dc', 'dc_office', 'network_segment']:
                    candidates.append((dist, cell))
        if not candidates: return None
        candidates.sort(key=lambda c: (c[0], c[1]['geometry'].get('width', 0) * c[1]['geometry'].get('height', 0)))
        return candidates[0][1]

    def get_report(self):
        return {'zones': len(self.zones), 'segments': len(self.segments), 'networks': len(self.networks), 'components': len(self.components), 'links': len(self.links), 'unknown': len(self.unknown), 'noise': len([c for c in self.cells if c.get('is_noise')]), 'badges': len(self.badges), 'services': len(self.services), 'kb': len(self.kbs), 'storage': len(self.storages), 'cluster': len(self.clusters), 'k8s': len(self.k8s_clusters)}
