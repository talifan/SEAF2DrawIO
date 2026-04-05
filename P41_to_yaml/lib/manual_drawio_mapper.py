import yaml
import re
import os

class ManualDrawioMapper:
    def __init__(self, classifier):
        self.classifier = classifier
        self.output_data = {}
        self.oid_registry = {}

    def map_all(self):
        self._map_roots()
        self._pre_generate_oids()
        self._map_locations()
        self._map_segments()
        self._map_networks()
        self._map_components()
        self._map_generic('seaf.company.ta.services.compute_services', self.classifier.services, 'project.compute_service')
        self._map_generic('seaf.company.ta.services.kb', self.classifier.kbs, 'project.kb')
        self._map_generic('seaf.company.ta.services.storages', self.classifier.storages, 'project.storage')
        self._map_generic('seaf.company.ta.services.cluster_virtualizations', self.classifier.clusters, 'project.cluster')
        self._map_generic('seaf.company.ta.services.k8s', self.classifier.k8s_clusters, 'project.k8s')
        self._map_generic('seaf.company.ta.services.backups', self.classifier.backups, 'project.backup')
        self._map_generic('seaf.company.ta.components.user_devices', getattr(self.classifier, 'user_devices', []), 'project.user_device')

    def _sanitize_oid(self, text):
        if not text: return ""
        translit_map = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
        text = text.lower(); res = ""
        for char in text:
            if char in translit_map: res += translit_map[char]
            elif char.isalnum() or char == '.': res += char
            else: res += '_'
        return re.sub(r'_+', '_', res).strip('_')

    def _generate_unique_oid(self, cell, prefix):
        val = str(cell.get('value', '')).strip()
        # Remove HTML tags from OID base
        val = re.sub(r'<[^>]*>', '', val)
        sanitized = self._sanitize_oid(val)
        if not sanitized: sanitized = self._sanitize_oid(cell.get('id', 'id'))
        suffix = cell.get('location_suffix')
        oid = f"{prefix}.{suffix}.{sanitized}" if suffix else f"{prefix}.{sanitized}"
        if oid in self.oid_registry and self.oid_registry[oid] != cell['id']:
            oid = f"{oid}_{self._sanitize_oid(cell.get('id'))[-6:]}"
        self.oid_registry[oid] = cell['id']; return oid

    def _map_roots(self):
        reg_oid = 'project.dc_region.auto_created'
        az_oid = 'project.dc_az.auto_created'
        self.output_data['seaf.company.ta.services.dc_regions'] = {reg_oid: {'title': 'Регион'}}
        self.output_data['seaf.company.ta.services.dc_azs'] = {az_oid: {'title': 'Зона Доступности', 'region': reg_oid}}
        self.auto_region = reg_oid; self.auto_az = az_oid

    def _pre_generate_oids(self):
        prefixes = {'dc': 'project.dc', 'dc_office': 'project.dc_office', 'network_segment': 'project.network_segment', 'network': 'project.network', 'network_component': 'project.network_component', 'compute_service': 'project.compute_service', 'kb': 'project.kb', 'storage': 'project.storage', 'cluster_virtualization': 'project.cluster', 'k8s': 'project.k8s', 'backup': 'project.backup', 'non_network_component': 'project.unknown_component', 'user_device': 'project.user_device', 'server': 'project.server'}
        for cell in self.classifier.zones: cell['seaf_oid'] = self._generate_unique_oid(cell, prefixes.get(cell['seaf_type'], 'project.loc'))
        for cell in self.classifier.segments: cell['seaf_oid'] = self._generate_unique_oid(cell, 'project.network_segment')
        collections = [self.classifier.networks, self.classifier.components, self.classifier.services, 
                       self.classifier.kbs, self.classifier.storages, self.classifier.clusters, self.classifier.k8s_clusters, self.classifier.backups, getattr(self.classifier, 'user_devices', []), getattr(self.classifier, 'servers', [])]
        for coll in collections:
            for cell in coll:
                stype = cell.get('seaf_type')
                if stype == 'non_network_component': stype = cell.get('component_subtype')
                if stype in prefixes: cell['seaf_oid'] = self._generate_unique_oid(cell, prefixes[stype])

    def _get_cell_by_id(self, cell_id):
        return next((c for c in self.classifier.cells if c['id'] == cell_id), None) if cell_id else None

    def _get_unique_title(self, cell, location_cell=None, segment_cell=None):
        # Extract plain text from HTML-heavy values
        val = str(cell.get('value', 'Unknown')).strip()
        val = re.sub(r'<[^>]*>', ' ', val)
        val = re.sub(r'\s+', ' ', val).strip()
        return val if val else "Unnamed"

    def _map_locations(self):
        dc_key, office_key = 'seaf.company.ta.services.dcs', 'seaf.company.ta.services.dc_offices'
        self.output_data[dc_key], self.output_data[office_key] = {}, {}
        for cell in self.classifier.zones:
            oid = cell.get('seaf_oid'); data = {'title': self._get_unique_title(cell), 'confidence_score': cell.get('confidence', 0.5)}
            if cell.get('seaf_type') == 'dc': data['availabilityzone'] = self.auto_az; self.output_data[dc_key][oid] = data
            else: data['region'] = self.auto_region; self.output_data[office_key][oid] = data

    def _map_segments(self):
        key = 'seaf.company.ta.services.network_segments'; self.output_data[key] = {}
        for cell in self.classifier.segments:
            oid = cell.get('seaf_oid'); p_id = cell.get('parent_location_id'); p_cell = self._get_cell_by_id(p_id)
            p_oid = p_cell.get('seaf_oid') if p_cell else None
            data = {'title': self._get_unique_title(cell), 'confidence_score': cell.get('confidence', 0.5)}
            stype = cell.get('segment_type', 'unknown')
            data['zone'] = stype.upper()
            if p_oid:
                data['location'] = p_oid
                if cell.get('is_external'): data['external'] = True
            else:
                all_locs = list(self.output_data.get('seaf.company.ta.services.dcs', {}).keys()) + list(self.output_data.get('seaf.company.ta.services.dc_offices', {}).keys())
                if all_locs:
                    data['location'] = all_locs[0]; data['external'] = True
            self.output_data[key][oid] = data

    def _map_networks(self):
        key = 'seaf.company.ta.services.networks'; self.output_data[key] = {}
        for cell in self.classifier.networks:
            oid, val_raw, det = cell.get('seaf_oid'), str(cell.get('value', '')), cell.get('network_details', {})
            s_cell = self._get_cell_by_id(cell.get('parent_segment_id'))
            l_cell = self._get_cell_by_id(cell.get('parent_location_id'))
            s_oid = s_cell.get('seaf_oid') if s_cell else None
            l_oid = l_cell.get('seaf_oid') if l_cell else None
            
            data = {'title': self._get_unique_title(cell), 'ipnetwork': det.get('cidr') or 'xxx.xxx.xxx.xxx/xx', 'confidence_score': cell.get('confidence', 0.5)}
            data['type'] = 'LAN' if not any(k in val_raw.lower() for k in ['wan', 'isp', 'sp']) else 'WAN'
            
            if det.get('vlan'):
                try: data['vlan'] = int(det['vlan'])
                except: data['vlan'] = det['vlan']
            if not s_oid:
                all_segs = list(self.output_data.get('seaf.company.ta.services.network_segments', {}).keys())
                if all_segs: s_oid = all_segs[0]
            if s_oid: data['segment'] = [s_oid]
            if l_oid: data['location'] = [l_oid]
            self.output_data[key][oid] = data

    def _map_components(self):
        key = 'seaf.company.ta.components.networks'; self.output_data[key] = {}
        for cell in self.classifier.components:
            oid = cell.get('seaf_oid'); s_cell = self._get_cell_by_id(cell.get('parent_segment_id')); l_cell = self._get_cell_by_id(cell.get('parent_location_id'))
            s_oid = s_cell.get('seaf_oid') if s_cell else None; l_oid = l_cell.get('seaf_oid') if l_cell else None
            net_conn = []
            for adj_id in self.classifier.adj.get(cell['id'], []):
                adj_c = self._get_cell_by_id(adj_id)
                if adj_c and adj_c.get('seaf_type') == 'network':
                    n_oid = adj_c.get('seaf_oid')
                    if n_oid and n_oid not in net_conn: net_conn.append(n_oid)
            pnet_id = cell.get('parent_network_id')
            if pnet_id:
                pnet = self._get_cell_by_id(pnet_id)
                if pnet and pnet.get('seaf_oid') and pnet.get('seaf_oid') not in net_conn:
                    net_conn.append(pnet.get('seaf_oid'))
            
            data = {'title': self._get_unique_title(cell), 'type': cell.get('component_subtype', 'unknown'), 'model': 'unknown', 'realization_type': 'Физический', 'confidence_score': cell.get('confidence', 0.5)}
            if not s_oid:
                all_segs = list(self.output_data.get('seaf.company.ta.services.network_segments', {}).keys())
                if all_segs: s_oid = all_segs[0]
            if not l_oid:
                all_locs = list(self.output_data.get('seaf.company.ta.services.dcs', {}).keys()) + list(self.output_data.get('seaf.company.ta.services.dc_offices', {}).keys())
                if all_locs: l_oid = all_locs[0]
            if s_oid: data['segment'] = s_oid
            if l_oid: data['location'] = [l_oid]
            if not net_conn:
                all_nets = list(self.output_data.get('seaf.company.ta.services.networks', {}).keys())
                if all_nets: net_conn = [all_nets[0]]
            if net_conn: data['network_connection'] = net_conn
            self.output_data[key][oid] = data

    def _map_generic(self, schema_key, collection, prefix):
        if not collection: return
        if schema_key not in self.output_data: self.output_data[schema_key] = {}
        for cell in collection:
            oid = cell.get('seaf_oid'); s_cell = self._get_cell_by_id(cell.get('parent_segment_id')); l_cell = self._get_cell_by_id(cell.get('parent_location_id'))
            s_oid = s_cell.get('seaf_oid') if s_cell else None; l_oid = l_cell.get('seaf_oid') if l_cell else None
            data = {'title': self._get_unique_title(cell), 'confidence_score': cell.get('confidence', 0.5)}
            if 'entity_fields' in cell: data.update(cell['entity_fields'])
            if not s_oid:
                all_segs = list(self.output_data.get('seaf.company.ta.services.network_segments', {}).keys())
                if all_segs: s_oid = all_segs[0]
            if not l_oid:
                all_locs = list(self.output_data.get('seaf.company.ta.services.dcs', {}).keys()) + list(self.output_data.get('seaf.company.ta.services.dc_offices', {}).keys())
                if all_locs: l_oid = all_locs[0]
            if s_oid: data['segment'] = s_oid
            if l_oid: data['location'] = [l_oid]
            net_conn = []
            for adj_id in self.classifier.adj.get(cell['id'], []):
                adj_c = self._get_cell_by_id(adj_id)
                if adj_c and adj_c.get('seaf_type') == 'network':
                    n_oid = adj_c.get('seaf_oid')
                    if n_oid and n_oid not in net_conn: net_conn.append(n_oid)
            pnet_id = cell.get('parent_network_id')
            if pnet_id:
                pnet = self._get_cell_by_id(pnet_id)
                if pnet and pnet.get('seaf_oid') and pnet.get('seaf_oid') not in net_conn:
                    net_conn.append(pnet.get('seaf_oid'))
            if not net_conn:
                all_nets = list(self.output_data.get('seaf.company.ta.services.networks', {}).keys())
                if all_nets: net_conn = [all_nets[0]]
            if net_conn: data['network_connection'] = net_conn
            if schema_key == 'seaf.company.ta.components.user_devices': data['device_type'] = 'АРМ'
            self.output_data[schema_key][oid] = data

    def save_yaml(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        file_map = {'seaf.company.ta.services.dc_regions': 'dc_region.yaml', 'seaf.company.ta.services.dc_azs': 'dc_az.yaml', 'seaf.company.ta.services.dcs': 'dc.yaml', 'seaf.company.ta.services.dc_offices': 'dc_office.yaml', 'seaf.company.ta.services.network_segments': 'network_segment.yaml', 'seaf.company.ta.services.networks': 'network.yaml', 'seaf.company.ta.components.networks': 'network_component.yaml', 'seaf.company.ta.services.compute_services': 'compute_service.yaml', 'seaf.company.ta.services.kb': 'kb.yaml', 'seaf.company.ta.services.storages': 'storage.yaml', 'seaf.company.ta.services.cluster_virtualizations': 'cluster_virtualization.yaml', 'seaf.company.ta.services.k8s': 'k8s.yaml', 'seaf.company.ta.services.backups': 'backup.yaml', 'seaf.company.ta.components.user_devices': 'user_device.yaml'}
        yaml_files = []; full_data = {}
        for key, filename in file_map.items():
            if key in self.output_data and self.output_data[key]:
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump({key: self.output_data[key]}, f, allow_unicode=True, sort_keys=False)
                yaml_files.append(filename); full_data[key] = self.output_data[key]
        with open(os.path.join(output_dir, 'seaf_full.yaml'), 'w', encoding='utf-8') as f:
            yaml.dump(full_data, f, allow_unicode=True, sort_keys=False)
        with open(os.path.join(output_dir, '_root.yaml'), 'w', encoding='utf-8') as f:
            yaml.dump({'imports': sorted(yaml_files)}, f, allow_unicode=True)
