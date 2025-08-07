import xml.etree.ElementTree as ET

def find_parent(root, target):
    """Находит родительский элемент для target в дереве root."""
    for elem in root.iter():
        for child in list(elem):
            if child is target:
                return elem
    return None

def collect_data_links(data):
    """Собирает все связи из данных для всех схем."""
    data_links = set()
    possible_keys = ['location', 'network_connection', 'connections', 'links', 'segment']

    segments = data.get('seaf.ta.services.network_segment', {})

    def segment_locations(seg_id):
        locs = []
        seg = segments.get(seg_id)
        if not seg:
            return locs
        def find_loc(attrs):
            if isinstance(attrs, dict):
                for k, v in attrs.items():
                    if k == 'location':
                        locs.extend(v if isinstance(v, list) else [v])
                    else:
                        find_loc(v)
            elif isinstance(attrs, list):
                for item in attrs:
                    find_loc(item)
        find_loc(seg)
        return locs

    def extract_links(source_id, attrs):
        if isinstance(attrs, dict):
            if 'source' in attrs and 'target' in attrs:
                src = attrs['source']
                targets = attrs['target'] if isinstance(attrs['target'], list) else [attrs['target']]
                for tgt in targets:
                    link_key = tuple(sorted([src, tgt]))
                    data_links.add(link_key)
            for key, value in attrs.items():
                if key in possible_keys:
                    connections = value if isinstance(value, list) else [value]
                    for target_id in connections:
                        link_key = tuple(sorted([source_id, target_id]))
                        data_links.add(link_key)
                        if key == 'segment':
                            for loc in segment_locations(target_id):
                                link_key2 = tuple(sorted([source_id, loc]))
                                data_links.add(link_key2)
                else:
                    extract_links(source_id, value)
        elif isinstance(attrs, list):
            for item in attrs:
                extract_links(source_id, item)

    for objects in data.values():
        if not isinstance(objects, dict):
            continue
        for source_id, attrs in objects.items():
            extract_links(source_id, attrs)

    return data_links

def remove_obsolete_links(diagram, data_file):
    """Удаляет связи из диаграммы, которые отсутствуют в данных."""
    existing_links = {}
    root = diagram.drawing

    for obj in root.iter('object'):
        cell = obj.find('mxCell')
        if cell is not None and cell.get('edge') == '1':
            source = cell.get('source')
            target = cell.get('target')
            if source and target:
                link_key = tuple(sorted([source, target]))
                existing_links[link_key] = obj.get('id')

    from lib import seaf_drawio
    d = seaf_drawio.SeafDrawio({})
    data_links = collect_data_links(d.read_and_merge_yaml(data_file))

    links_to_remove = set(existing_links.keys()) - data_links

    if links_to_remove:
        print(f"Удаляем {len(links_to_remove)} устаревших связей:")
        for link_key in links_to_remove:
            print(f"  {link_key[0]} -> {link_key[1]}")
    else:
        print("Нет устаревших связей для удаления.")

    for link_key in links_to_remove:
        link_id = existing_links[link_key]
        for obj in root.findall(f'.//object[@id="{link_id}"]'):
            parent = find_parent(root, obj)
            if parent is not None:
                parent.remove(obj)

