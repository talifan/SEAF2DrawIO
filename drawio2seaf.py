from lib import seaf_drawio
import sys
import argparse

# Переменные по умолчанию
DEFAULT_CONFIG = {
    "drawio2seaf": {
        "drawio_file": "result/Sample_graph.drawio",
        "schema_file" : 'data/seaf_schema.yaml',
        "output_file": "result/seaf.yaml"
    }
}
d = seaf_drawio.SeafDrawio(DEFAULT_CONFIG)
#diagram = drawio_diagram()


def __cli_vars(config):
    try:
        parser = argparse.ArgumentParser(description="Параметры командной строки.")

        dst_validator = d.create_validator(r'^.+(\.yaml)$')
        src_validator = d.create_validator(r'^.+(\.drawio)$')

        parser.add_argument("-s", "--src", type=src_validator, action=seaf_drawio.ValidateFile, help="файл DrawIO",
                            required=False)
        parser.add_argument("-d", "--dst", type=dst_validator, help="путь и имя файла вывода результатов",
                            required=False)
        parser.add_argument("-p", "--pattern", type=dst_validator, action=seaf_drawio.ValidateFile,
                            help="шаблон схемы yaml",
                            required=False)
        args = parser.parse_args()
        if args.src:
            config['drawio_file'] = args.src
        if args.dst:
            config['output_file'] = args.dst
        if args.pattern:
            config['drawio_pattern'] = args.pattern
        return config

    except argparse.ArgumentTypeError as e:
        print(e)
        sys.exit(1)


if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = __cli_vars(d.load_config("config.yaml")['drawio2seaf'])
    network_connections = d.get_network_connections(conf['drawio_file'], '100')
    objects_data = d.get_data_from_diagram(conf['drawio_file'])
    json_schemas = d.get_json_schemas(conf['schema_file'])

    yaml_dict = {}
    for schema_key, schema in json_schemas.items():

        for d_key, d_val in objects_data.get(schema_key, {}).items():
            # Добавляем в объект фактические связи между объектами
            if d_val.get('network_connection') and d_key in network_connections:
                d_val['network_connection'] = str(network_connections[d_key])

            yaml_dict = d.merge_dicts(yaml_dict,{schema_key: {d_key: d.remove_empty_fields(d.populate_json(schema, d_val))}})

    d.write_to_yaml_file(conf['output_file'], yaml_dict)




