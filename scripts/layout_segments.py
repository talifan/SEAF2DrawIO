#!/usr/bin/env python3
"""Normalize segment geometry on DrawIO pages before content layout."""
import ast
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.drawio_utils import find_diagram, float_attr, format_number, get_geometry
from lib.schemas import SeafSchema

SEGMENT_SCHEMA = SeafSchema.NETWORK_SEGMENT
SEGMENT_PADDING_X = 20.0
SEGMENT_PADDING_RIGHT = 20.0
BOTTOM_MARGIN = 40.0
MIN_SEGMENT_HEIGHT = 160.0
FLOW_ITEM_GAP_Y = 20.0
MAX_INT_NET_STACK_ITEMS = 5
EXTERNAL_INTERNET_CIDR = "0.0.0.0/0"
INTERNET_ITEM_GAP_X = 20.0
INTERNET_ITEM_GAP_Y = 20.0
INTERNET_TRANSPORT_GAP = 20.0
INTERNET_EXTERNAL_OUTSIDE_GAP = 40.0


def get_rotation(style):
    match = re.search(r"rotation=([0-9.]+)", style or "")
    return float(match.group(1)) if match else 0.0


def get_layout_box(cell):
    geom = get_geometry(cell)
    if geom is None:
        return 0.0, 0.0
    width = float_attr(geom, "width")
    height = float_attr(geom, "height")
    if get_rotation(cell.get("style", "")) % 180 == 90.0:
        return height, width
    return width, height


def get_visual_position(cell):
    geom = get_geometry(cell)
    if geom is None:
        return 0.0, 0.0
    x = float_attr(geom, "x")
    y = float_attr(geom, "y")
    raw_w = float_attr(geom, "width")
    raw_h = float_attr(geom, "height")
    if get_rotation(cell.get("style", "")) % 180 == 90.0:
        offset = (raw_w - raw_h) / 2.0
        return x + offset, y - offset
    return x, y


def parse_keywords(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, str):
        items = [part.strip().lower() for part in raw_value.split(",")]
    else:
        items = [str(part).strip().lower() for part in raw_value]
    return [item for item in items if item]


def parse_list_literal(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
    except Exception:
        return [str(value)]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def match_diagram(name, keywords):
    if not keywords:
        return True
    title = (name or "").lower()
    return any(keyword in title for keyword in keywords)


def resolve_target_diagrams(mxfile_root, diagram_arg, keywords):
    diagram_value = (diagram_arg or "").strip()
    normalized = parse_keywords(keywords)
    if not diagram_value or diagram_value.lower() == "all":
        diagrams = [
            diagram
            for diagram in mxfile_root.findall("diagram")
            if match_diagram(diagram.get("name", ""), normalized)
        ]
        if not diagrams:
            raise SystemExit("No diagrams matched the provided filters.")
        return diagrams

    names = [part.strip() for part in diagram_value.split(",") if part.strip()]
    if not names:
        raise SystemExit("Diagram name is empty.")

    found = []
    for name in names:
        diagram = find_diagram(mxfile_root, name)
        if diagram is None:
            raise SystemExit(f"Diagram '{name}' not found")
        found.append(diagram)
    return found


def collect_segments(root_cell):
    segments = {}
    for elem in root_cell:
        if elem.tag != "object":
            continue
        if elem.get("schema") != SEGMENT_SCHEMA:
            continue
        cell = elem.find("mxCell")
        geom = get_geometry(cell)
        if cell is None or geom is None:
            continue
        segments[elem.get("id")] = {
            "object": elem,
            "cell": cell,
            "geom": geom,
            "zone": elem.get("zone") or "",
            "id": elem.get("id") or "",
        }
    return segments


def measure_segment_content(root_cell, segment_id):
    bottom = 0.0
    right = 0.0
    for elem in root_cell:
        if elem.tag == "object":
            cell = elem.find("mxCell")
            if cell is None or cell.get("parent") != segment_id:
                continue
        elif elem.tag == "mxCell":
            if elem.get("parent") != segment_id:
                continue
            cell = elem
        else:
            continue

        visual_x, visual_y = get_visual_position(cell)
        layout_w, layout_h = get_layout_box(cell)
        right = max(right, visual_x + layout_w)
        bottom = max(bottom, visual_y + layout_h)

    return right, bottom


def get_reference_network_height(root_cell, segments):
    int_net_segment_ids = {
        segment_id
        for segment_id, segment in segments.items()
        if segment["zone"] == "INT-NET"
    }
    int_net_heights = []
    fallback_heights = []

    for elem in root_cell:
        if elem.tag != "object":
            continue
        if elem.get("schema") != SeafSchema.NETWORK:
            continue
        cell = elem.find("mxCell")
        if cell is None:
            continue
        parent_id = cell.get("parent") or ""
        if parent_id not in segments:
            continue
        _, layout_h = get_layout_box(cell)
        if layout_h <= 0:
            continue
        fallback_heights.append(layout_h)
        if parent_id in int_net_segment_ids:
            int_net_heights.append(layout_h)

    if int_net_heights:
        return max(int_net_heights)
    if fallback_heights:
        return max(fallback_heights)
    return 200.0


def update_segment_geometry(segment, *, x=None, y=None, w=None, h=None):
    geom = segment["geom"]
    changed = False
    updates = {"x": x, "y": y, "width": w, "height": h}
    for key, value in updates.items():
        if value is None:
            continue
        current = float_attr(geom, key)
        if abs(current - value) < 0.01:
            continue
        geom.set(key, format_number(value))
        changed = True
    return changed


def collect_cells_by_id(root_cell):
    cells = {}
    object_cells = {}
    objects = {}
    for elem in root_cell:
        if elem.tag == "mxCell":
            cell_id = elem.get("id")
            if cell_id:
                cells[cell_id] = elem
            continue
        object_id = elem.get("id")
        if object_id:
            objects[object_id] = elem
        cell = elem.find("mxCell")
        if cell is None:
            continue
        if object_id:
            object_cells[object_id] = cell
        cell_id = cell.get("id")
        if cell_id:
            cells[cell_id] = cell
    return cells, object_cells, objects


def resolve_parent_cell(parent_id, cells_by_id, object_cells_by_id):
    return cells_by_id.get(parent_id) or object_cells_by_id.get(parent_id)


def get_absolute_visual_position(cell, cells_by_id, object_cells_by_id):
    x, y = get_visual_position(cell)
    parent_id = cell.get("parent") or ""
    visited = set()
    while parent_id and parent_id not in visited:
        visited.add(parent_id)
        parent_cell = resolve_parent_cell(parent_id, cells_by_id, object_cells_by_id)
        if parent_cell is None:
            break
        parent_x, parent_y = get_visual_position(parent_cell)
        x += parent_x
        y += parent_y
        parent_id = parent_cell.get("parent") or ""
    return x, y


def set_visual_position(cell, x=None, y=None):
    geom = get_geometry(cell)
    if geom is None:
        return False
    raw_w = float_attr(geom, "width")
    raw_h = float_attr(geom, "height")
    offset = 0.0
    if get_rotation(cell.get("style", "")) % 180 == 90.0:
        offset = (raw_w - raw_h) / 2.0

    changed = False
    if x is not None:
        target_x = x - offset
        current_x = float_attr(geom, "x")
        if abs(current_x - target_x) >= 0.01:
            geom.set("x", format_number(target_x))
            changed = True
    if y is not None:
        target_y = y + offset
        current_y = float_attr(geom, "y")
        if abs(current_y - target_y) >= 0.01:
            geom.set("y", format_number(target_y))
            changed = True
    return changed


def collect_segment_direct_items(root_cell, segment_id, objects_by_id):
    items = []
    for elem in root_cell:
        cell = None
        bound_object = None

        if elem.tag == "mxCell":
            if elem.get("parent") != segment_id or elem.get("edge") == "1":
                continue
            cell = elem
            cell_id = elem.get("id") or ""
            if cell_id.endswith("_0"):
                bound_object = objects_by_id.get(cell_id[:-2])
        elif elem.tag == "object":
            cell = elem.find("mxCell")
            if cell is None or cell.get("parent") != segment_id:
                continue
            bound_object = elem
        else:
            continue

        geom = get_geometry(cell)
        if geom is None:
            continue
        local_x, local_y = get_visual_position(cell)
        layout_w, layout_h = get_layout_box(cell)
        items.append(
            {
                "element": elem,
                "cell": cell,
                "object": bound_object,
                "id": (bound_object.get("id") if bound_object is not None else cell.get("id")) or "",
                "local_x": local_x,
                "local_y": local_y,
                "layout_w": layout_w,
                "layout_h": layout_h,
            }
        )
    return items


def belongs_to_internet_segment(bound_object, segment_id, objects_by_id):
    if bound_object is None:
        return False
    if (bound_object.get("segment") or "") == segment_id:
        return True
    if bound_object.get("internet_external") != "true":
        return False
    connections = parse_list_literal(bound_object.get("network_connection"))
    if not connections:
        return False
    network_object = objects_by_id.get(connections[0])
    return network_object is not None and (network_object.get("segment") or "") == segment_id


def collect_internet_segment_items(root_cell, segment_id, container_parent, objects_by_id):
    items = []
    parent_ids = {segment_id, container_parent}
    seen = set()
    for elem in root_cell:
        cell = None
        bound_object = None

        if elem.tag == "mxCell":
            if elem.get("parent") not in parent_ids or elem.get("edge") == "1":
                continue
            cell = elem
            cell_id = elem.get("id") or ""
            if cell_id.endswith("_0"):
                bound_object = objects_by_id.get(cell_id[:-2])
        elif elem.tag == "object":
            cell = elem.find("mxCell")
            if cell is None or cell.get("parent") not in parent_ids:
                continue
            bound_object = elem
        else:
            continue

        if not belongs_to_internet_segment(bound_object, segment_id, objects_by_id):
            continue

        item_key = (bound_object.get("id") if bound_object is not None else cell.get("id")) or ""
        if item_key in seen:
            continue
        seen.add(item_key)

        geom = get_geometry(cell)
        if geom is None:
            continue
        local_x, local_y = get_visual_position(cell)
        layout_w, layout_h = get_layout_box(cell)
        items.append(
            {
                "element": elem,
                "cell": cell,
                "object": bound_object,
                "id": item_key,
                "local_x": local_x,
                "local_y": local_y,
                "layout_w": layout_w,
                "layout_h": layout_h,
            }
        )
    return items


def is_external_internet_item(item):
    obj = item.get("object")
    if obj is None:
        return False
    if obj.get("internet_external") == "true":
        return True
    return (
        obj.get("schema") == SeafSchema.NETWORK
        and (obj.get("ipnetwork") or "").strip() == EXTERNAL_INTERNET_CIDR
    )


def flow_layout_items(items, segment_width, start_y):
    current_x = SEGMENT_PADDING_X
    current_y = max(SEGMENT_PADDING_X, start_y)
    row_height = 0.0
    max_right = max(SEGMENT_PADDING_X, segment_width - SEGMENT_PADDING_RIGHT)

    for item in items:
        item_width = item["layout_w"]
        item_height = item["layout_h"]
        max_x = max(SEGMENT_PADDING_X, max_right - item_width)
        if current_x > SEGMENT_PADDING_X and current_x + item_width > max_right + 0.01:
            current_y += row_height + INTERNET_ITEM_GAP_Y
            current_x = SEGMENT_PADDING_X
            row_height = 0.0
            max_x = max(SEGMENT_PADDING_X, max_right - item_width)

        item["target_x"] = min(current_x, max_x)
        item["target_y"] = current_y
        current_x = item["target_x"] + item_width + INTERNET_ITEM_GAP_X
        row_height = max(row_height, item_height)

    if not items:
        return current_y
    return current_y + row_height + INTERNET_ITEM_GAP_Y


def get_internet_segment_anchor(segment):
    visual_x, visual_y = get_visual_position(segment["cell"])
    return visual_x, visual_y


def collect_page_level_internet_external_items(
    segments, cells_by_id, object_cells_by_id, objects_by_id
):
    segment_items = {}
    for obj in objects_by_id.values():
        if obj.get("internet_external") != "true":
            continue
        group_cell = cells_by_id.get(f"{obj.get('id')}_0")
        if group_cell is None or get_geometry(group_cell) is None:
            continue

        connections = parse_list_literal(obj.get("network_connection"))
        if not connections:
            continue
        network_object = objects_by_id.get(connections[0])
        if network_object is None:
            continue
        segment_id = network_object.get("segment") or ""
        segment = segments.get(segment_id)
        if segment is None or (segment.get("zone") or "").upper() != "INTERNET":
            continue

        abs_x, abs_y = get_absolute_visual_position(group_cell, cells_by_id, object_cells_by_id)
        layout_w, layout_h = get_layout_box(group_cell)
        segment_items.setdefault(segment_id, []).append(
            {
                "cell": group_cell,
                "object": obj,
                "id": obj.get("id") or "",
                "abs_x": abs_x,
                "abs_y": abs_y,
                "layout_w": layout_w,
                "layout_h": layout_h,
            }
        )
    return segment_items


def normalize_internet_segment_contents(root_cell, segments, cells_by_id, object_cells_by_id, objects_by_id):
    changed = False
    page_level_external_items = collect_page_level_internet_external_items(
        segments, cells_by_id, object_cells_by_id, objects_by_id
    )

    for segment_id, segment in segments.items():
        if (segment.get("zone") or "").upper() != "INTERNET":
            continue
        anchor_x, anchor_y = get_internet_segment_anchor(segment)
        container_parent = segment["cell"].get("parent") or segment_id
        segment_width, _ = get_layout_box(segment["cell"])
        items = collect_internet_segment_items(root_cell, segment_id, container_parent, objects_by_id)
        items.extend(page_level_external_items.get(segment_id, []))
        unique_items = {}
        for item in items:
            unique_items.setdefault(item["id"], item)
        items = list(unique_items.values())
        if not items:
            continue
        outside_items = sorted(
            [
                item
                for item in items
                if item.get("object") is not None and item["object"].get("internet_external") == "true"
            ],
            key=lambda item: (
                item.get("local_y", item.get("abs_y", 0.0)),
                item.get("local_x", item.get("abs_x", 0.0)),
                item["id"],
            ),
        )
        inside_external_items = sorted(
            [
                item
                for item in items
                if is_external_internet_item(item)
                and not (item.get("object") is not None and item["object"].get("internet_external") == "true")
            ],
            key=lambda item: (
                item.get("local_y", item.get("abs_y", 0.0)),
                item.get("local_x", item.get("abs_x", 0.0)),
                item["id"],
            ),
        )
        regular_items = sorted(
            [item for item in items if not is_external_internet_item(item)],
            key=lambda item: (
                item.get("local_y", item.get("abs_y", 0.0)),
                item.get("local_x", item.get("abs_x", 0.0)),
                item["id"],
            ),
        )
        outside_y = anchor_y + SEGMENT_PADDING_X
        for item in outside_items:
            if item["cell"].get("parent") != container_parent:
                item["cell"].set("parent", container_parent)
                changed = True
            changed |= set_visual_position(
                item["cell"],
                x=anchor_x - INTERNET_EXTERNAL_OUTSIDE_GAP - item["layout_w"],
                y=outside_y,
            )
            outside_y += item["layout_h"] + INTERNET_ITEM_GAP_Y

        next_y = SEGMENT_PADDING_X
        next_y = flow_layout_items(inside_external_items, segment_width, next_y)
        flow_layout_items(regular_items, segment_width, next_y)

        for item in inside_external_items + regular_items:
            if item["cell"].get("parent") != container_parent:
                item["cell"].set("parent", container_parent)
                changed = True
            changed |= set_visual_position(
                item["cell"],
                x=anchor_x + item["target_x"],
                y=anchor_y + item["target_y"],
            )

    return changed


def ensure_internet_transport_gap(segments, cells_by_id, object_cells_by_id):
    internet = find_first_segment(segments, "INTERNET")
    transport = find_first_segment(segments, "TRANSPORT-WAN")
    if internet is None or transport is None:
        return False

    internet_left, _ = get_absolute_visual_position(internet["cell"], cells_by_id, object_cells_by_id)
    transport_left, _ = get_absolute_visual_position(transport["cell"], cells_by_id, object_cells_by_id)
    internet_width, _ = get_layout_box(internet["cell"])
    target_left = internet_left + internet_width + INTERNET_TRANSPORT_GAP
    delta = target_left - transport_left
    if abs(delta) < 0.01:
        return False
    return update_segment_geometry(transport, x=float_attr(transport["geom"], "x") + delta)


def find_first_segment(segments, zone_name):
    matches = [seg for seg in segments.values() if seg["zone"] == zone_name]
    if not matches:
        return None
    return sorted(matches, key=lambda item: (float_attr(item["geom"], "x"), float_attr(item["geom"], "y"), item["id"]))[0]


def find_management_int_net(segments, primary_int_net_id):
    matches = []
    for segment in segments.values():
        if segment["zone"] != "INT-NET":
            continue
        if segment["id"] == primary_int_net_id:
            continue
        title = (segment["object"].get("title") or "").lower()
        seg_id = segment["id"].lower()
        if "management" in title or "management" in seg_id:
            matches.append(segment)
    if not matches:
        return None
    return sorted(matches, key=lambda item: (float_attr(item["geom"], "x"), float_attr(item["geom"], "y"), item["id"]))[0]


def normalize_page_segments(root_cell):
    segments = collect_segments(root_cell)
    if not segments:
        return False, "no segments"

    inet = find_first_segment(segments, "INET-EDGE")
    ext = find_first_segment(segments, "EXT-WAN-EDGE")
    dmz = find_first_segment(segments, "DMZ")
    int_wan = find_first_segment(segments, "INT-WAN-EDGE")
    int_net = find_first_segment(segments, "INT-NET")
    int_security = find_first_segment(segments, "INT-SECURITY-NET")
    management_int_net = find_management_int_net(segments, int_net["id"] if int_net is not None else "")

    changed = False
    bounds = {}
    reference_network_height = get_reference_network_height(root_cell, segments)
    max_int_net_height = (
        SEGMENT_PADDING_X
        + MAX_INT_NET_STACK_ITEMS * reference_network_height
        + max(0, MAX_INT_NET_STACK_ITEMS - 1) * FLOW_ITEM_GAP_Y
        + BOTTOM_MARGIN
    )

    for segment_id, segment in segments.items():
        current_w = float_attr(segment["geom"], "width")
        content_right, content_bottom = measure_segment_content(root_cell, segment_id)
        target_w = max(current_w, content_right + SEGMENT_PADDING_RIGHT)
        target_h = max(MIN_SEGMENT_HEIGHT, content_bottom + BOTTOM_MARGIN)
        bounds[segment_id] = {"w": target_w, "h": target_h}

    if int_net is not None:
        bounds[int_net["id"]]["h"] = min(bounds[int_net["id"]]["h"], max_int_net_height)
        height_ceiling = bounds[int_net["id"]]["h"]
    else:
        height_ceiling = max_int_net_height

    for segment_id, bound in bounds.items():
        if int_net is not None and segment_id == int_net["id"]:
            continue
        bound["h"] = min(bound["h"], height_ceiling)

    if inet and dmz:
        inet_x = float_attr(inet["geom"], "x")
        dmz_x = float_attr(dmz["geom"], "x")
        if dmz_x > inet_x:
            bounds[inet["id"]]["w"] = max(bounds[inet["id"]]["w"], dmz_x - inet_x)
        changed |= update_segment_geometry(
            inet,
            w=bounds[inet["id"]]["w"],
            h=bounds[inet["id"]]["h"],
        )

    if inet and ext:
        ext_height = bounds[ext["id"]]["h"]
        changed |= update_segment_geometry(
            ext,
            x=float_attr(inet["geom"], "x"),
            y=float_attr(inet["geom"], "y") + float_attr(inet["geom"], "height"),
            w=float_attr(inet["geom"], "width"),
            h=ext_height,
        )

    if dmz and int_wan:
        changed |= update_segment_geometry(
            dmz,
            x=float_attr(inet["geom"], "x") + float_attr(inet["geom"], "width") if inet is not None else None,
            w=bounds[dmz["id"]]["w"],
            h=bounds[dmz["id"]]["h"],
        )
        changed |= update_segment_geometry(
            int_wan,
            x=float_attr(dmz["geom"], "x"),
            y=float_attr(dmz["geom"], "y") + float_attr(dmz["geom"], "height"),
            w=float_attr(dmz["geom"], "width"),
            h=bounds[int_wan["id"]]["h"],
        )

    if dmz and int_net:
        min_int_net_height = float_attr(dmz["geom"], "height")
        if int_wan is not None:
            min_int_net_height = max(
                min_int_net_height,
                float_attr(int_wan["geom"], "y") + float_attr(int_wan["geom"], "height"),
            )
        changed |= update_segment_geometry(
            int_net,
            x=float_attr(dmz["geom"], "x") + float_attr(dmz["geom"], "width"),
            y=float_attr(dmz["geom"], "y"),
            w=bounds[int_net["id"]]["w"],
            h=max(bounds[int_net["id"]]["h"], min_int_net_height),
        )

    if int_net and int_security:
        changed |= update_segment_geometry(
            int_security,
            x=float_attr(int_net["geom"], "x") + float_attr(int_net["geom"], "width"),
            y=float_attr(int_net["geom"], "y"),
            w=bounds[int_security["id"]]["w"],
            h=max(bounds[int_security["id"]]["h"], float_attr(int_net["geom"], "height")),
        )

    if management_int_net:
        neighbor = int_security if int_security is not None else int_net
        if neighbor is not None:
            changed |= update_segment_geometry(
                management_int_net,
                x=float_attr(neighbor["geom"], "x") + float_attr(neighbor["geom"], "width"),
                y=float_attr(neighbor["geom"], "y"),
                w=bounds[management_int_net["id"]]["w"],
                h=float_attr(neighbor["geom"], "height"),
            )

    # Update standalone segments not covered by dependency logic.
    anchored_ids = {
        seg["id"]
        for seg in (inet, ext, dmz, int_wan, int_net, int_security, management_int_net)
        if seg is not None
    }

    for segment_id, segment in segments.items():
        if segment_id in anchored_ids:
            continue
        changed |= update_segment_geometry(
            segment,
            w=bounds[segment_id]["w"],
            h=bounds[segment_id]["h"],
        )

    cells_by_id, object_cells_by_id, objects_by_id = collect_cells_by_id(root_cell)
    changed |= ensure_internet_transport_gap(segments, cells_by_id, object_cells_by_id)
    changed |= normalize_internet_segment_contents(
        root_cell, segments, cells_by_id, object_cells_by_id, objects_by_id
    )

    return changed, "normalized" if changed else "already aligned"


def process_diagram(diagram):
    model = diagram.find("mxGraphModel")
    if model is None:
        return False, "missing mxGraphModel"
    root_cell = model.find("root")
    if root_cell is None:
        return False, "missing root"
    return normalize_page_segments(root_cell)


def main():
    parser = argparse.ArgumentParser(description="Normalize segment geometry on DrawIO pages.")
    parser.add_argument("-i", "--input", required=True, help="Path to .drawio file")
    parser.add_argument("--diagram", default="all", help="Comma-separated page names or 'all'")
    parser.add_argument("--diagram-filter", default="", help="Comma-separated name keywords")
    args = parser.parse_args()

    tree = ET.parse(args.input)
    mxfile_root = tree.getroot()

    changed_any = False
    for diagram in resolve_target_diagrams(mxfile_root, args.diagram, args.diagram_filter):
        changed, reason = process_diagram(diagram)
        changed_any = changed_any or changed
        print(f"[{diagram.get('name')}] segment layout {reason}.")

    if changed_any:
        tree.write(args.input, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
