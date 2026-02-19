#!/usr/bin/env python3
"""Duplicate technical service objects inside a DrawIO file to stress-test layouts."""
import argparse
import copy
import sys
import os
import xml.etree.ElementTree as ET

# Adjust path to import lib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.schemas import SeafSchema
from lib.drawio_utils import find_diagram

TARGET_SCHEMAS = {
    SeafSchema.COMPUTE_SERVICE,
    SeafSchema.CLUSTER_VIRTUALIZATION,
    SeafSchema.K8S,
    SeafSchema.MONITORING,
    SeafSchema.BACKUP,
}

ATTRS_TO_PATCH = ("id", "parent", "source", "target", "value", "label")


def patch_attributes(element, base_id, suffix):
    for attr, value in list(element.attrib.items()):
        if value and base_id in value:
            element.set(attr, value.replace(base_id, base_id + suffix))
    for child in element:
        patch_attributes(child, base_id, suffix)

def parse_keywords(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, str):
        tokens = [token.strip().lower() for token in raw_value.split(",")]
    else:
        tokens = [str(token).strip().lower() for token in raw_value]
    return [token for token in tokens if token]


def match_diagram(name, keywords):
    if not keywords:
        return True
    title = (name or "").lower()
    return any(keyword in title for keyword in keywords)


def resolve_target_diagrams(mxfile_root, diagram_arg, keywords):
    diag_value = (diagram_arg or "").strip()
    normalized = parse_keywords(keywords)
    if not diag_value or diag_value.lower() == "all":
        diagrams = [
            diagram
            for diagram in mxfile_root.findall("diagram")
            if match_diagram(diagram.get("name", ""), normalized)
        ]
        if not diagrams:
            raise SystemExit(
                "No diagrams matched the provided keywords; "
                "use --diagram to target a specific page."
            )
        return diagrams

    names = [part.strip() for part in diag_value.split(",") if part.strip()]
    if not names:
        raise SystemExit("Diagram name is empty; provide --diagram value or use 'all'")
    
    # Use imported find_diagram
    found = []
    for name in names:
        d = find_diagram(mxfile_root, name)
        if d is None:
             raise SystemExit(f"Diagram '{name}' not found")
        found.append(d)
    return found


def gather_related_elements(root, base_id):
    related = []
    for elem in root:
        elem_id = elem.get("id")
        if elem_id and base_id in elem_id:
            related.append(elem)
    return related


def duplicate_object(root, obj, factor):
    base_id = obj.get("id")
    if not base_id:
        return 0
    related = gather_related_elements(root, base_id)
    if obj not in related:
        related.append(obj)
    child_list = list(root)
    position_map = {id(elem): idx for idx, elem in enumerate(child_list)}
    related.sort(key=lambda el: position_map.get(id(el), 0))
    insert_pos = position_map.get(id(related[-1]), len(child_list) - 1) + 1
    created = 0
    for dup_idx in range(1, factor):
        suffix = f"__dup{dup_idx}"
        for elem in related:
            clone = copy.deepcopy(elem)
            patch_attributes(clone, base_id, suffix)
            root.insert(insert_pos, clone)
            insert_pos += 1
            created += 1
    return created


def duplicate_services(diagram, factor, schemas):
    mx_graph = diagram.find("mxGraphModel")
    if mx_graph is None:
        raise SystemExit("mxGraphModel node not found")
    root_cell = mx_graph.find("root")
    originals = [elem for elem in root_cell if elem.tag == "object" and elem.get("schema") in schemas]
    duplicates = 0
    for obj in originals:
        duplicates += duplicate_object(root_cell, obj, factor)
    return len(originals) * (factor - 1), duplicates


def parse_args():
    parser = argparse.ArgumentParser(description="Duplicate DrawIO services for stress testing")
    parser.add_argument("-i", "--input", default="result/Sample_graph.drawio", help="Source DrawIO file")
    parser.add_argument("-o", "--output", default="result/Sample_graph_stress.drawio", help="Output DrawIO file")
    parser.add_argument("--diagram", default="all", help="Target diagram name or 'all'")
    parser.add_argument(
        "--diagram-filter",
        default="DC,ЦОД",
        help="Comma separated keywords for selecting diagrams when --diagram=all",
    )
    parser.add_argument("--factor", type=int, default=3, help="Replication factor")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.factor < 2:
        raise SystemExit("Factor must be >= 2")
    tree = ET.parse(args.input)
    root = tree.getroot()
    diagrams = resolve_target_diagrams(root, args.diagram, args.diagram_filter)
    stats = []
    for diagram in diagrams:
        originals_added, elements_added = duplicate_services(diagram, args.factor, TARGET_SCHEMAS)
        stats.append((diagram.get("name", "<unnamed>"), originals_added, elements_added))
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    for name, originals_added, elements_added in stats:
        print(
            f"[{name}] Duplicated {originals_added} objects (added {elements_added} XML nodes) into '{args.output}'"
        )
