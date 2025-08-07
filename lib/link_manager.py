import xml.etree.ElementTree as ET


def find_parent(root, target):
    """Находит родительский элемент для target в дереве root."""
    for elem in root.iter():
        for child in list(elem):
            if child is target:
                return elem
    return None


def collect_data_links(object_data):
    """Собирает множество связей из данных объекта."""
    data_links = set()
    for source_id, targets in object_data.items():
        possible_keys = ["location", "network_connection", "connections", "links"]
        for key in possible_keys:
            if key in targets:
                connections = targets[key]
                if not isinstance(connections, list):
                    connections = [connections]
                for target_id in connections:
                    link_key = tuple(sorted([source_id, target_id]))
                    data_links.add(link_key)
    return data_links


def remove_obsolete_links(diagram, data_file, schema_key):
    """
    Удаляет из диаграммы связи, отсутствующие в новых данных.

    :param diagram: Экземпляр drawio_diagram
    :param data_file: Путь к YAML-файлу с данными
    :param schema_key: Ключ схемы для поиска связей в данных
    """
    from lib import seaf_drawio

    d = seaf_drawio.SeafDrawio({})
    object_data = d.get_object(data_file, schema_key)
    object_ids = set(object_data.keys())

    data_links = collect_data_links(object_data)

    existing_links = {}
    root = diagram.drawing
    for obj in root.iter("object"):
        cell = obj.find("mxCell")
        if cell is not None and cell.get("edge") == "1":
            source = cell.get("source")
            target = cell.get("target")
            if not (source and target):
                continue
            if source not in object_ids and target not in object_ids:
                continue
            link_key = tuple(sorted([source, target]))
            existing_links[link_key] = obj.get("id")

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

