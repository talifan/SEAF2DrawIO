from N2G import drawio_diagram
import sys
import re
import os
import argparse
import subprocess
from copy import deepcopy
from typing import Optional, Dict, List, Set, Any
from lib import seaf_drawio
from lib.link_manager import remove_obsolete_links, draw_verify, advanced_analysis
from lib.schemas import SeafSchema
from lib.drawio_utils import format_number, float_attr
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

patterns_dir = 'data/patterns/'
diagram = drawio_diagram()
node_xml_default = diagram.drawio_node_object_xml
root_object = SeafSchema.DC_REGION
diagram_pages = {'main': ['Main Schema'], 'office': [], 'dc': []}
diagram_ids = {'Main Schema': set()}
conf = {}
pending_missing_links = set()
layout_counters = {}
expected_counts = {}
expected_data = {}
pattern_specs = {}
data_store = None
link_style_override = ''

# Переменные по умолчанию
DEFAULT_CONFIG = {
    "seaf2drawio": {
        "data_yaml_file": "data/example/test_seaf_ta_P41_v0.9.yaml",
        "drawio_pattern": "data/base.drawio",
        "output_file": "result/Sample_graph.drawio",
        "verify_generation": False,
        "auto_layout_grid": False
    }
}

d = seaf_drawio.SeafDrawio(DEFAULT_CONFIG)

def cli_vars(config):
    try:
        parser = argparse.ArgumentParser(description="Параметры командной строки.")

        src_validator = d.create_validator(r'^.+(\.yaml)$')
        dst_validator = d.create_validator(r'^.+(\.drawio)$')

        parser.add_argument("-s", "--src", type=src_validator, action=seaf_drawio.ValidateFile, help="файл данных SEAF",
                            required=False)
        parser.add_argument("-d", "--dst", type=dst_validator, help="путь и имя файла вывода результатов",
                            required=False)
        parser.add_argument("-p", "--pattern", type=dst_validator, action=seaf_drawio.ValidateFile, help="шаблон drawio",
                            required=False)
        parser.add_argument("--debug", action="store_true", help="включить подробную диагностику")
        args = parser.parse_args()
        if args.src:
            config['data_yaml_file'] = args.src
        if args.dst:
            config['output_file'] = args.dst
        if args.pattern:
            config['drawio_pattern'] = args.pattern
        if args.debug:
            config['debug'] = True
        return config

    except argparse.ArgumentTypeError as e:
        print(e)
        sys.exit(1)


def adjust_link_style(style):
    if not style or link_style_override != 'straight':
        return style
    tokens = []
    for token in style.split(';'):
        token = token.strip()
        if not token:
            continue
        if token.startswith('edgeStyle='):
            continue
        if token.startswith('curved='):
            continue
        if token.startswith('rounded='):
            continue
        if token.startswith('jumpStyle='):
            continue
        if token.startswith('orthogonalLoop='):
            continue
        if token.startswith('jettySize='):
            continue
        tokens.append(token)
    tokens.insert(0, 'edgeStyle=straight')
    tokens.append('curved=0')
    tokens.append('rounded=0')
    return ';'.join(tokens) + ';'

def position_offset(pattern):

    match pattern['algo']:
        # По оси Y cверху вниз относительно родительского объекта
        case 'Y+':
            if return_ready(pattern):
                pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']
                pattern['y'] = pattern['y'] - (pattern['h'] + pattern['offset']) * pattern['deep']
            pattern['y'] = pattern['y'] + pattern['h'] + pattern['offset']

        case 'Y-':
            if return_ready(pattern):
                pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']
                pattern['y'] = pattern['y'] + (pattern['h'] + pattern['offset']) * pattern['deep']
            pattern['y'] = pattern['y'] - pattern['h'] - pattern['offset']

        case 'X-':

            if return_ready(pattern):
                pattern['y'] = pattern['y'] +  pattern['h'] + pattern['offset']
                pattern['x'] = pattern['x'] + (pattern['w'] + pattern['offset']) * pattern['deep']
            pattern['x'] = pattern['x'] - pattern['w'] - pattern['offset']
        # По оси X слева направо
        case 'X+':
            if return_ready(pattern):
                pattern['y'] = pattern['y'] +  pattern['h'] + pattern['offset']
                pattern['x'] = pattern['x'] - (pattern['w'] + pattern['offset']) * pattern['deep']
            pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']

def return_ready(pattern):
    pattern['count']+=1
    if pattern['count'] == pattern['deep']:
        pattern['count'] = 0

    return not bool(pattern['count'])

def get_parent_value(pattern, current_parent):
    if not (pattern.get('parent_key') and current_parent):
        return ''

    parent_data = d.find_value_by_key(data_store, current_parent) if data_store else None
    if parent_data is None:
        return ''
    parent_value = d.find_value_by_key(parent_data, pattern['parent_key'])
    return parent_value if parent_value is not None else ''

def add_pages(pattern):

    if pattern.get('ext_page'):
        page_data = d.get_object(conf['data_yaml_file'], pattern['schema'])
        diagram_xml_default = diagram.drawio_diagram_xml

        for key_id in list( page_data.keys() ):

            diagram.drawio_diagram_xml = pattern['ext_page']
            try:
                diagram.add_diagram(key_id + '_page', page_data[key_id]['title'])
                diagram_pages[k].append(page_data[key_id]['title'])
                diagram_ids.setdefault(page_data[key_id]['title'], set()).add(key_id)
            except ET.ParseError:
                print(f'WARNING ! Не используйте XML зарезервированные символы <>&\'\" в поле title для объектов dc/office')
                pass


        diagram.drawio_diagram_xml = diagram_xml_default
        diagram.go_to_diagram(page_name)

def add_object(pattern: Dict[str, Any], data: Dict[str, Any], key_id: str) -> None:

    pattern_count, current_parent = 0, ''
    for xml_pattern in d.get_xml_pattern(pattern['xml'], key_id):

        diagram.drawio_node_object_xml = xml_pattern

        # Если у элемента есть родитель, получаем ID родителя и проверяем связан ли родитель с текущей диаграммой (страницей)
        # добавляем в справочник ID элемента
        if pattern.get('parent_id') and d.find_common_element(d.find_key_value(data, pattern['parent_id']),
                                                     list(diagram_ids[page_name])) and pattern_count == 0:

            diagram_ids.setdefault(page_name, set()).add(key_id)
            current_parent = d.find_common_element(d.find_key_value(data, pattern['parent_id']),list(diagram_ids[page_name]))

            # If parent_id field is a list (e.g., WAN.segment), normalize it to the selected current_parent
            try:
                if isinstance(data.get(pattern['parent_id']), list):
                    data['parent_tmp'] = data.get(pattern['parent_id'])
                    data[pattern['parent_id']] = current_parent
            except Exception:
                pass

            parent_value = get_parent_value(pattern, current_parent)

            if current_parent != pattern['last_parent'] and pattern['parent_id'] != 'network_connection':
                # Для паттернов с parent_key (например, ISP->zone) один и тот же контейнер
                # может использоваться при разных parent_id. Сохраняем/восстанавливаем позицию
                # отдельно для каждого фактического контейнера.
                if not pattern.get('global_positioning'):
                    pos_map = pattern.setdefault('_position_by_parent_type', {})
                    if parent_value in pos_map:
                        saved = pos_map[parent_value]
                        pattern['x'] = saved.get('x', pattern['x'])
                        pattern['y'] = saved.get('y', pattern['y'])
                        pattern['count'] = saved.get('count', pattern.get('count', 0))
                    else:
                        default_pattern['parent'] = parent_value
                        pattern.update(default_pattern)

                pattern['last_parent'] = current_parent

            pattern['parent'] = parent_value
            pattern['last_parent_type'] = parent_value


        try:
            # Escape data for XML, including quotes for attributes
            safe_data = {k: saxutils.escape(str(v), entities={'"': "&quot;", "'": "&apos;"}) if v is not None else '' for k, v in data.items()}
            
            diagram.drawio_node_object_xml = diagram.drawio_node_object_xml.format_map(
                safe_data | {'Group_ID': f'{key_id}_0', 'parent_id' : current_parent, 'parent_type' : pattern.get('parent', ''),
                        'description' : saxutils.escape(str(data.get('description','') or ''), entities={'"': "&quot;", "'": "&apos;"}) })
            data['OID'] = key_id
            
            # Pre-escape title for N2G add_node which inserts it into XML
            safe_title = saxutils.escape(str(data.get('title', '')), entities={'"': "&quot;", "'": "&apos;"})

        except KeyError as e:

            #print("Error: Can't add object: {id} to page: {page}. Key: {key} out of dictionary. Data: {data}"
            #      .format(key=str(e), id=i, page=page_name, data=data))
            return


        if key_id in diagram_ids[page_name]:

            #if pattern.get('parent_id') == 'dc':
            #    print(f'==={i} == {current_parent} === {key_id}_{pattern_count}')
            """
                Заменяет ключ 'id' на 'sid' в словаре, если он существует.
            """
            if 'id' in data:
                data['sid'] = data.pop('id')

            data['schema'] = pattern['schema']

            # Удаляем техническое поле если оно присутствует в данных
            if 'parent_tmp' in data:
                del data['parent_tmp']

            # Если не содержит конструкции <object></object>, то изменять ID добавляя порядковый номер

            diagram.add_node(
                id=f"{key_id}_{pattern_count}" if not d.contains_object_tag(xml_pattern, 'object') else key_id,
                label=safe_title,
                x_pos=pattern['x'],
                y_pos=pattern['y'],
                width=pattern['w'],
                height=pattern['h'],
                data=data if d.contains_object_tag(xml_pattern, 'object') else {},
                url=pattern.get('ext_page') and data['title']
            )
            diagram_ids.setdefault(page_name, set()).add(key_id)  # Добавляет ID root элементов

            if pattern_count == 0:  # Change position of element
                position_offset(object_pattern)
            if pattern.get('parent'):
                pos_map = pattern.setdefault('_position_by_parent_type', {})
                pos_map[pattern['parent']] = {
                    'x': pattern['x'],
                    'y': pattern['y'],
                    'count': pattern.get('count', 0),
                }
            pattern_count += 1

        diagram.drawio_node_object_xml = node_xml_default

def add_links(pattern: Dict[str, Any], **kwargs: bool) -> None:

    diagram.drawio_link_object_xml = pattern['xml']
    schema_name = pattern['schema']
    type_filter = object_pattern.get('type')

    if kwargs.get('network_link'):
        schema_name = SeafSchema.NETWORK_LINK
        type_filter = None

    source_id = 'Unknown'
    source_objects = d.get_object(conf['data_yaml_file'], schema_name, type=type_filter)

    if not isinstance(source_objects, dict):
        return

    eligible_links = None
    if kwargs.get('network_link'):
        eligible_links = {}
        for link_id, link_value in source_objects.items():
            connections = link_value.get(pattern['targets']) or []
            present_count = sum(1 for node_id in connections if node_id in diagram_ids[page_name])
            if present_count >= 2:
                eligible_links[link_id] = link_value
        if eligible_links:
            expected_counts.setdefault(schema_name, set()).update(list(eligible_links.keys()))
            expected_data.setdefault(schema_name, {}).update(eligible_links)

    drawn_pairs = set()

    for source_id, targets in source_objects.items():  # source_id - ID объекта

        if kwargs.get('logical_link'):
            targets['OID'] = source_id
            source_id = targets['source']
            targets['schema'] = pattern['schema']

        if kwargs.get('network_link'):
            link_data = targets
            link_data.setdefault('OID', source_id)
            link_data.setdefault('schema', schema_name)
            connections = link_data.get(pattern['targets']) or []
            if not isinstance(connections, list):
                continue
            normalized_connections = [conn for conn in connections if conn]
            if len(normalized_connections) < 2:
                continue
            anchor = next((conn for conn in normalized_connections if conn in diagram_ids[page_name]), None)
            if not anchor:
                # все объекты отсутствуют на текущей странице, откладываем проверку
                for target_id in normalized_connections[1:]:
                    pending_missing_links.add((page_name, normalized_connections[0], target_id))
                continue

            style = pattern.get('style', '')
            technology = link_data.get('technology')
            if technology:
                tech_key = f"style.{technology}"
                style = pattern.get(tech_key, style)
            style = adjust_link_style(style)

            label = link_data.get('title', '')

            for target_id in normalized_connections:
                if target_id == anchor:
                    continue
                pair_key = tuple(sorted((anchor, target_id)))
                if pair_key in drawn_pairs:
                    continue
                if target_id in diagram_ids[page_name]:
                    diagram.add_link(source=anchor, target=target_id, style=style, label=label, data=link_data)
                else:
                    pending_missing_links.add((page_name, anchor, target_id))
                drawn_pairs.add(pair_key)
            continue

        try:
            if source_id in diagram_ids[page_name]:  # Объект присутствует на текущей диаграмме
                if pattern.get('parent_id'):
                    # parent_id may be a list (e.g., WAN.segment). Derive targets for each parent entry.
                    parent_val = targets.get(pattern['parent_id'])
                    parent_ids = parent_val if isinstance(parent_val, list) else ([parent_val] if parent_val else [])
                    derived_targets = []
                    for pid in parent_ids:
                        val = get_parent_value(pattern, pid)
                        if isinstance(val, list):
                            derived_targets.extend(val)
                        elif val is not None:
                            derived_targets.append(val)
                    targets = {pattern['targets']: derived_targets}
                for target_id in targets[pattern['targets']]:
                    if target_id in diagram_ids[page_name]:  # Объект для связи присутствует на диаграмме
                        if kwargs.get('logical_link'):
                            style = 'style'+ str(targets['direction']) # Выбор стиля стрелки
                            style_value = adjust_link_style(pattern[style])
                            diagram.add_link(source=source_id, target=target_id, style=style_value, data=targets)
                        else:
                            base_style = adjust_link_style(pattern['style'])
                            diagram.add_link(source=source_id, target=target_id, style=base_style)
                    else:
                        # Defer logging: cross-page targets are expected; warn later only if missing everywhere
                        pending_missing_links.add((page_name, source_id, target_id))
                        #print(f' Can\'t link  {source_id} <---> {target_id}, object {target_id} not found at the page '
                        #      f'{page_name}')
        except KeyError as e:
            pass
            print(f" INFO : Не найден параметр {e} для объекта '{pattern['schema']}/{source_id}' при добавлении связей на диаграмму '{page_name}'.")
        except TypeError as e:
            pass
            print(
                f"Error: у объекта '{source_id}' отсутствует данные для создания линка в параметре {pattern['targets']} ")

def collect_ids():
    try:
        schema_key = object_pattern['schema']
        expected_counts.setdefault(schema_key, set()).update(list(object_data.keys()))
        expected_data.setdefault(schema_key, {}).update(object_data)
        # Record pattern spec for diagnostics
        type_key, type_val = None, None
        if object_pattern.get('type'):
            if ':' in object_pattern['type']:
                type_key, type_val = object_pattern['type'].split(':', 1)
            else:
                type_key, type_val = 'type', object_pattern['type']
        pattern_specs.setdefault(schema_key, []).append({
            'pattern_name': k,
            'parent_id': object_pattern.get('parent_id'),
            'type_key': type_key,
            'type_val': type_val,
        })
    except Exception as Ex:
        print(f"Exception Collect ID : {Ex}")


def run_auto_layout_if_enabled(conf: Dict[str, Any]) -> None:
    if not conf.get('auto_layout_grid'):
        return

    script_path = conf.get('auto_layout_script', os.path.join('scripts', 'layout_tech_services.py'))
    cmd = [sys.executable, '-X', 'utf8', script_path, '-i', conf['output_file']]

    if conf.get('auto_layout_diagram'):
        cmd.extend(['--diagram', conf['auto_layout_diagram']])
    if conf.get('auto_layout_filter'):
        cmd.extend(['--diagram-filter', conf['auto_layout_filter']])

    print("\n> Запускаю автоматическую раскладку по сетке ...")
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.stdout:
            print(completed.stdout.rstrip())
        if completed.returncode != 0:
            print(f"WARNING: auto-layout завершился с кодом {completed.returncode}")
            if completed.stderr:
                print(completed.stderr.rstrip())
    except Exception as ex:
        print(f"WARNING: не удалось запустить auto-layout: {ex}")


if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = cli_vars(d.load_config("config.yaml")['seaf2drawio'])
    link_style_override = (conf.get('link_style') or '').lower()

    data_store = d.get_merged_yaml(conf['data_yaml_file'])

    diagram.from_xml(d.read_file_with_utf8(conf['drawio_pattern']))
    
    # Удаляем устаревшие связи перед добавлением новых
    remove_obsolete_links(diagram, conf['data_yaml_file'], 'seaf.company.ta.components.networks')
    
    diagram_ids['Main Schema'] = set(d.get_object(conf['data_yaml_file'], root_object).keys())
    for file_name, pages in diagram_pages.items():

        for page_name in pages:

            diagram.go_to_diagram(page_name)
            print(f"\n> Формирую диаграмму страницы \033[32m{page_name}\033[0m ", end='')
            pattern_definitions = d.get_pattern(patterns_dir + file_name + '.yaml')
            for k, object_pattern in pattern_definitions.items():
                print('.', end='')
                try:
                    object_data = d.get_object(conf['data_yaml_file'], object_pattern['schema'], type=object_pattern.get('type'),
                        sort=object_pattern['parent_id'] if object_pattern.get('parent_id') else None)

                    add_pages(object_pattern)
                    object_pattern.update({
                                'count': 0,               # Счетчик объектов
                                'last_parent': '',        # Триггер для отслеживания изменения родительского объекта
                                'last_parent_type': '',   # Последний фактический контейнер (parent_key)
                                '_position_by_parent_type': {},
                                'parent': ''              # Родительский объект
                    })
                    default_pattern = deepcopy(object_pattern)

                    # Collect expected IDs and data per schema (for verification)
                    collect_ids()

                    for i in list(object_data.keys()):
                        if i in diagram.nodes_ids[diagram.current_diagram_id]:
                            diagram.update_node(id=i, data=object_data[i])
                            diagram_ids.setdefault(page_name, set()).add(i)
                        else:
                            add_object(object_pattern, object_data[i], i)

                except KeyError as e:
                    pass
                    print(f' INFO : В файле данных отсутствуют объекты {object_pattern["schema"]} для добавления на диаграмму {page_name}')

                if bool(re.match(r'^network_links(_\d+)*',k)):
                    add_links(object_pattern, pattern_name=k)  # Связывание объектов на текущей диаграмме
                    if k == 'network_links':
                        add_links(object_pattern, network_link=True)  # Дополнительные связи из seaf.ta.services.network_links

                if bool(re.match(r'^logical_links(_\d+)*', k)):
                    add_links(object_pattern, logical_link=True)  # Связывание объектов на текущей диаграмме

    print('\n')
    # Verifying drawn links & objects ...
    draw_verify(diagram_ids, diagram, pending_missing_links)

    d.dump_file(filename=os.path.basename(conf['output_file']), folder=os.path.dirname(conf['output_file']),
                content=diagram.drawing if os.path.dirname(conf['output_file']) else './')

    run_auto_layout_if_enabled(conf)

    # Check additional result info ...
    advanced_analysis(conf, expected_counts, expected_data, pattern_specs, d)
