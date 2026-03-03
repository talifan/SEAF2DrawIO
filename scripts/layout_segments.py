#!/usr/bin/env python3
"""Normalize segment geometry on DrawIO pages before content layout."""
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
