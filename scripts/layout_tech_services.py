#!/usr/bin/env python3
"""Re-layout technical services on a DrawIO page by grouping them inside target segments."""
import argparse
import ast
import hashlib
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

NODE_W = 40
NODE_H = 40
GAP_X = 20
GAP_Y = 20
PAD_X = 20
PAD_Y = 12
HEADER_H = 22
SEGMENT_PADDING_X = 20
SEGMENT_PADDING_RIGHT = 20
TECH_GAP_TOP = 40
ROW_GAP = 32
COL_GAP = 32
BOTTOM_MARGIN = 40
MAX_COLS = 4
MIN_CONTAINER_WIDTH = 170
APPEND_RIGHT_GAP = 40

TARGET_SCHEMAS = {
    "seaf.ta.services.compute_service": {
        "group_by": ["service_type"],
        "group_name": "Прочие сервисы",
        "auto_segment": True,
    },
    "seaf.ta.services.cluster": {
        "group_by": ["service_type"],
        "group_name": "Кластеры приложений",
        "auto_segment": True,
    },
    "seaf.ta.services.cluster_virtualization": {
        "group_name": "Платформы виртуализации",
        "auto_segment": True,
    },
    "seaf.ta.services.k8s": {
        "group_name": "Контейнерные платформы",
        "auto_segment": True,
    },
    "seaf.ta.services.monitoring": {
        "group_name": "Мониторинг",
        "auto_segment": True,
    },
    "seaf.ta.services.backup": {
        "group_name": "Резервное копирование",
        "auto_segment": True,
    },
    "seaf.ta.services.kb": {
        "group_by": ["technology", "tag"],
        "group_name": "Средства кибербезопасности",
        "auto_segment": True,
    },
}

ZONE_RULES = {
    "INET-EDGE": {
        "layout_mode": "stack_down",
        "neighbors_right_zones": ["DMZ"],
    },
    "INT-NET": {
        "layout_mode": "append_right",
        "tech_top": SEGMENT_PADDING_X,
        "append_width": 1400,
        "neighbors_right_zones": ["INT-SECURITY-NET"],
    },
    "DMZ": {
        "layout_mode": "append_right",
        "tech_top": SEGMENT_PADDING_X,
        "append_width": 400,
        "stack_below_zones": ["INT-WAN-EDGE"],
        "neighbors_right_zones": ["INT-NET"],
    },
    "INT-SECURITY-NET": {
        "layout_mode": "append_right",
        "tech_top": SEGMENT_PADDING_X,
        "append_width": 800,
    },
}

SECURITY_ZONE_HINTS = {
    "DMZ": (
        "waf",
        "web application firewall",
        "reverse proxy",
        "secure gateway",
    ),
    "INT-SECURITY-NET": (
        "ids",
        "ips",
        "siem",
        "antivirus",
        "dlp",
        "socc",
        "crypto",
        "крипто",
        "разгранич",
    ),
}


def parse_list_literal(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, (list, tuple, set)):
        return list(raw_value)
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if text.startswith("[") or text.startswith("(") or text.startswith("{"):
            try:
                data = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                data = [raw_value]
        else:
            return [raw_value]
        if isinstance(data, (list, tuple, set)):
            return list(data)
        return [data]
    return [raw_value]


def slugify(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def parse_metadata(obj):
    sber_attr = obj.get("sber")
    location = ""
    zone = ""
    if sber_attr:
        try:
            data = ast.literal_eval(sber_attr)
            location = data.get("location", "") if isinstance(data, dict) else ""
            zone = data.get("zone", "") if isinstance(data, dict) else ""
        except (ValueError, SyntaxError):
            pass
    return zone or "", location or ""


def build_segment_zone_index(objects_by_id):
    segment_meta = {}
    zone_index = defaultdict(list)
    for seg_id, obj in objects_by_id.items():
        if obj is None or obj.get("schema") != "seaf.ta.services.network_segment":
            continue
        zone, location = parse_metadata(obj)
        segment_meta[seg_id] = {"zone": zone, "location": location}
        cell = obj.find("mxCell")
        if cell is None:
            continue
        geom = get_geometry(cell)
        if geom is None:
            continue
        x = float_attr(geom, "x")
        zone_index[(zone, location)].append((x, seg_id))
    for key, items in zone_index.items():
        items.sort(key=lambda pair: pair[0])
        zone_index[key] = [seg_id for _, seg_id in items]
    return segment_meta, zone_index


def collect_cells(root):
    cells, objects = {}, {}
    for elem in root:
        if elem.tag == "object":
            obj_id = elem.get("id")
            objects[obj_id] = elem
            for child in elem:
                if child.tag == "mxCell" and child.get("id"):
                    cells[child.get("id")] = child
        elif elem.tag == "mxCell" and elem.get("id"):
            cells[elem.get("id")] = elem
    return cells, objects


def find_diagram(mxfile_root, name):
    for diagram in mxfile_root.findall("diagram"):
        if diagram.get("name") == name:
            return diagram
    raise SystemExit(f"Diagram '{name}' not found")


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
    return [find_diagram(mxfile_root, name) for name in names]


def get_geometry(cell):
    if cell is None:
        return None
    return cell.find("mxGeometry")


def float_attr(geom, key, default=0.0):
    if geom is None:
        return default
    try:
        return float(geom.get(key, default))
    except (TypeError, ValueError):
        return default


def compute_group_box(count, node_w, node_h):
    if count == 0:
        return 0, 0, []
    cols = max(1, min(MAX_COLS, math.ceil(math.sqrt(count))))
    rows = math.ceil(count / cols)
    inner_w = node_w if cols == 1 else cols * node_w + (cols - 1) * GAP_X
    inner_h = node_h if rows == 1 else rows * node_h + (rows - 1) * GAP_Y
    width = max(MIN_CONTAINER_WIDTH, inner_w + 2 * PAD_X)
    height = HEADER_H + PAD_Y + inner_h + PAD_Y
    positions = []
    for idx in range(count):
        col = idx % cols
        row = idx // cols
        x = PAD_X + col * (node_w + GAP_X)
        y = HEADER_H + PAD_Y + row * (node_h + GAP_Y)
        positions.append((x, y))
    return width, height, positions


def segment_content_bottom(root_cell, segment_id):
    bottom = 0.0
    for elem in root_cell:
        if elem.tag == "object":
            for child in elem:
                if child.tag != "mxCell" or child.get("parent") != segment_id:
                    continue
                geom = get_geometry(child)
                if geom is None:
                    continue
                y = float_attr(geom, "y")
                h = float_attr(geom, "height")
                bottom = max(bottom, y + h)
        elif elem.tag == "mxCell" and elem.get("parent") == segment_id:
            geom = get_geometry(elem)
            if geom is None:
                continue
            y = float_attr(geom, "y")
            h = float_attr(geom, "height")
            bottom = max(bottom, y + h)
    return bottom


def measure_segment_content(root_cell, segment_id):
    bottom = 0.0
    right = 0.0
    for elem in root_cell:
        if elem.tag == "object":
            for child in elem:
                if child.tag != "mxCell" or child.get("parent") != segment_id:
                    continue
                geom = get_geometry(child)
                if geom is None:
                    continue
                y = float_attr(geom, "y")
                h = float_attr(geom, "height")
                bottom = max(bottom, y + h)
                x = float_attr(geom, "x")
                w = float_attr(geom, "width")
                right = max(right, x + w)
        elif elem.tag == "mxCell" and elem.get("parent") == segment_id:
            geom = get_geometry(elem)
            if geom is None:
                continue
            y = float_attr(geom, "y")
            h = float_attr(geom, "height")
            bottom = max(bottom, y + h)
            x = float_attr(geom, "x")
            w = float_attr(geom, "width")
            right = max(right, x + w)
    return bottom, right


def shift_neighbor_chain(objects_by_id, start_geom, segment_rules, gap=SEGMENT_PADDING_X):
    neighbors = segment_rules.get("neighbors_right", [])
    current_x = float_attr(start_geom, "x") + float_attr(start_geom, "width") + gap
    last_extent = current_x
    for neighbor_id in neighbors:
        neighbor_obj = objects_by_id.get(neighbor_id)
        if neighbor_obj is None:
            continue
        geom = get_geometry(neighbor_obj.find("mxCell"))
        if geom is None:
            continue
        width = float_attr(geom, "width")
        geom.set("x", format_number(current_x))
        current_x += width + gap
        last_extent = current_x - gap
    return last_extent


def shift_stack_below(objects_by_id, base_geom, segment_rules, gap=SEGMENT_PADDING_X):
    stack_ids = segment_rules.get("stack_below", [])
    if not stack_ids:
        return float_attr(base_geom, "y") + float_attr(base_geom, "height")
    current_y = float_attr(base_geom, "y") + float_attr(base_geom, "height") + gap
    max_bottom = current_y - gap
    for neighbor_id in stack_ids:
        neighbor_obj = objects_by_id.get(neighbor_id)
        if neighbor_obj is None:
            continue
        geom = get_geometry(neighbor_obj.find("mxCell"))
        if geom is None:
            continue
        height = float_attr(geom, "height")
        geom.set("y", format_number(current_y))
        current_y += height + gap
        max_bottom = current_y - gap
    return max_bottom


def resolve_segment_rules(segment_id, segment_meta, zone_index):
    meta = segment_meta.get(segment_id, {})
    zone = meta.get("zone", "")
    location = meta.get("location", "")
    base = ZONE_RULES.get(zone)
    if not base:
        return {}
    rules = {k: v for k, v in base.items() if not k.endswith("_zones")}

    def ids_for_zones(zones):
        ids = []
        for zone_name in zones:
            for candidate in zone_index.get((zone_name, location), []):
                if candidate != segment_id:
                    ids.append(candidate)
        return ids

    if "neighbors_right_zones" in base:
        rules["neighbors_right"] = ids_for_zones(base["neighbors_right_zones"])
    if "stack_below_zones" in base:
        rules["stack_below"] = ids_for_zones(base["stack_below_zones"])
    return rules


def apply_security_hints(obj, segment_id, segment_meta, zone_index, derived_from_network=False):
    if not segment_id or obj.get("schema") != "seaf.ta.services.kb":
        return segment_id
    tag = (obj.get("tag") or "").lower()
    tech = (obj.get("technology") or "").lower()
    requested_zones = []
    for zone_name, keywords in SECURITY_ZONE_HINTS.items():
        if any(keyword in tag or keyword in tech for keyword in keywords):
            requested_zones.append(zone_name)
    if derived_from_network:
        return segment_id
    if not requested_zones:
        return segment_id
    current_meta = segment_meta.get(segment_id, {})
    current_zone = current_meta.get("zone", "")
    location = current_meta.get("location", "")
    if derived_from_network and current_zone in {"DMZ", "INT-SECURITY-NET"}:
        return segment_id
    for zone_name in requested_zones:
        candidates = zone_index.get((zone_name, location), [])
        if candidates:
            return candidates[0]
    return segment_id


def get_segments_bounds(objects_by_id):
    min_x = float("inf")
    max_x = float("-inf")
    max_bottom = 0.0
    for obj in objects_by_id.values():
        if obj is None or obj.get("schema") != "seaf.ta.services.network_segment":
            continue
        cell = obj.find("mxCell")
        if cell is None or cell.get("parent") != "001":
            continue
        geom = get_geometry(cell)
        x = float_attr(geom, "x")
        y = float_attr(geom, "y")
        width = float_attr(geom, "width")
        height = float_attr(geom, "height")
        min_x = min(min_x, x)
        max_x = max(max_x, x + width)
        max_bottom = max(max_bottom, y + height)
    return min_x if min_x != float("inf") else 0.0, max_x, max_bottom


def format_number(value):
    if isinstance(value, int) or value.is_integer():
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def add_container(root_cell, segment_id, group_id, label, x, y, width, height):
    style = (
        "rounded=1;dashed=1;html=1;whiteSpace=wrap;strokeColor=#7f8c8d;"
        "strokeWidth=1;fillColor=none;align=left;verticalAlign=top;"
        "spacingTop=6;spacingLeft=10;spacingRight=8;spacingBottom=6;"
        "fontFamily=Helvetica;fontSize=12;fontColor=#323130;"
    )
    cell = ET.Element(
        "mxCell",
        {
            "id": group_id,
            "value": f"<div><b>{label}</b></div>",
            "style": style,
            "vertex": "1",
            "parent": segment_id,
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": format_number(x),
            "y": format_number(y),
            "width": format_number(width),
            "height": format_number(height),
            "as": "geometry",
        },
    )
    root_cell.append(cell)
    return cell


def resolve_group_key(obj, schema_conf):
    for key in schema_conf.get("group_by", []):
        value = obj.get(key)
        if value:
            return value
    return schema_conf.get("group_name", obj.get("schema", "Прочие сервисы"))


def find_primary_cell(obj, cells_by_id):
    obj_id = obj.get("id")
    if not obj_id:
        return None
    cell = cells_by_id.get(f"{obj_id}_0")
    if cell is not None:
        return cell
    for child in obj:
        if child.tag == "mxCell":
            return child
    return None


def build_connection_segment_index(root_cell):
    lookup = {}
    for elem in root_cell:
        if elem.tag != "object":
            continue
        obj_id = elem.get("id")
        if not obj_id:
            continue
        segment_attr = elem.get("segment")
        if not segment_attr:
            continue
        segments = parse_list_literal(segment_attr)
        if not segments:
            continue
        lookup[obj_id] = segments[0]
    return lookup


def derive_segment_from_connections(obj, schema_conf, net_lookup):
    if not schema_conf.get("auto_segment"):
        return ""
    connections = parse_list_literal(obj.get("network_connection"))
    segs = []
    for conn in connections:
        seg = net_lookup.get(conn)
        if seg:
            segs.append(seg)
    if not segs:
        return ""
    counter = Counter(segs)
    best = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return best


def process_diagram(diagram, args):
    diagram_name = diagram.get("name", "<unnamed>")
    result = {"name": diagram_name, "total_items": 0, "segments": 0, "changed": False, "reason": ""}
    mx_graph = diagram.find("mxGraphModel")
    if mx_graph is None:
        result["reason"] = "mxGraphModel node not found"
        print(f"[{diagram_name}] WARNING: {result['reason']}")
        return result
    root_cell = mx_graph.find("root")
    if root_cell is None:
        result["reason"] = "mxGraphModel root not found"
        print(f"[{diagram_name}] WARNING: {result['reason']}")
        return result

    # Remove old containers to keep the script idempotent
    for cell in list(root_cell):
        if cell.tag == "mxCell" and (cell.get("id") or "").startswith("tech_group_"):
            root_cell.remove(cell)

    cells_by_id, objects_by_id = collect_cells(root_cell)
    net_segment_lookup = build_connection_segment_index(root_cell)
    segment_meta, zone_index = build_segment_zone_index(objects_by_id)

    managed_items = []
    for elem in root_cell:
        if elem.tag != "object":
            continue
        schema = elem.get("schema")
        if schema not in TARGET_SCHEMAS:
            continue
        primary_cell = find_primary_cell(elem, cells_by_id)
        if primary_cell is None:
            continue
        geom = get_geometry(primary_cell)
        width = max(NODE_W, float_attr(geom, "width", NODE_W))
        height = max(NODE_H, float_attr(geom, "height", NODE_H))
        schema_conf = TARGET_SCHEMAS[schema]
        segment_id = schema_conf.get("segment_id") or args.segment_id
        derived_segment = derive_segment_from_connections(elem, schema_conf, net_segment_lookup)
        derived_from_network = False
        if derived_segment:
            segment_id = derived_segment
            derived_from_network = True
        segment_id = apply_security_hints(elem, segment_id, segment_meta, zone_index, derived_from_network)
        neighbor_id = schema_conf.get("neighbor_segment_id") or None
        managed_items.append(
            {
                "object": elem,
                "cell": primary_cell,
                "schema": schema,
                "group": resolve_group_key(elem, schema_conf),
                "width": width,
                "height": height,
                "segment_id": segment_id,
                "neighbor_id": neighbor_id,
            }
        )

    if not managed_items:
        result["reason"] = "technical services not found on the page"
        print(f"[{diagram_name}] {result['reason']}; nothing to reflow.")
        return result

    dc_cell = cells_by_id.get(args.dc_container_id)
    dc_geom = get_geometry(dc_cell)
    dc_height = float_attr(dc_geom, "height") if dc_geom is not None else 0.0
    dc_width = float_attr(dc_geom, "width") if dc_geom is not None else 0.0
    max_needed_height = dc_height
    dc_inner_extent = dc_width
    total_items = 0
    processed_segments = 0

    segments = defaultdict(lambda: {"items": [], "neighbor": None})
    for item in managed_items:
        seg_id = item["segment_id"]
        entry = segments[seg_id]
        entry["items"].append(item)
        if entry["neighbor"] is None:
            entry["neighbor"] = item["neighbor_id"] or args.neighbor_segment_id

    def segment_sort_key(seg_id):
        obj = objects_by_id.get(seg_id)
        if obj is None:
            return 0.0
        geom = get_geometry(obj.find("mxCell"))
        return float_attr(geom, "x", 0.0)

    ordered_segment_ids = sorted(segments.keys(), key=segment_sort_key)

    for segment_id in ordered_segment_ids:
        seg_data = segments[segment_id]
        items = seg_data["items"]
        if not items:
            continue

        segment_obj = objects_by_id.get(segment_id)
        if segment_obj is None:
            print(f"[{diagram_name}] WARNING: segment '{segment_id}' not found; skipping {len(items)} items")
            continue
        segment_cell = segment_obj.find("mxCell")
        segment_geom = get_geometry(segment_cell)
        segment_height = float_attr(segment_geom, "height")
        segment_width = float_attr(segment_geom, "width")
        segment_x = float_attr(segment_geom, "x")
        existing_bottom, base_width = measure_segment_content(root_cell, segment_id)
        segment_rules = resolve_segment_rules(segment_id, segment_meta, zone_index)
        layout_mode = segment_rules.get("layout_mode", "stack_down")

        groups = defaultdict(list)
        for item in items:
            groups[item["group"]].append(item)

        ordered_groups = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        layout = {}
        append_anchor = base_width
        if layout_mode == "append_right":
            row_x = append_anchor + APPEND_RIGHT_GAP
        else:
            row_x = SEGMENT_PADDING_X
        row_y = 0.0
        row_height = 0.0
        if layout_mode == "append_right":
            wrap_limit = append_anchor + segment_rules.get(
                "append_width",
                segment_width - SEGMENT_PADDING_RIGHT,
            )
            wrap_limit = max(wrap_limit, row_x + MIN_CONTAINER_WIDTH)
        else:
            wrap_limit = segment_width - SEGMENT_PADDING_RIGHT

        for label, group_items in ordered_groups:
            slot_w = max(entry["width"] for entry in group_items)
            slot_h = max(entry["height"] for entry in group_items)
            width, height, positions = compute_group_box(len(group_items), slot_w, slot_h)
            min_x = append_anchor + APPEND_RIGHT_GAP if layout_mode == "append_right" else SEGMENT_PADDING_X
            if row_x + width > wrap_limit and row_x > min_x:
                row_y += row_height + ROW_GAP
                row_x = min_x
                row_height = 0.0
            layout[label] = {
                "rel_x": row_x,
                "rel_y": row_y,
                "width": width,
                "height": height,
                "positions": positions,
                "slot_w": slot_w,
                "slot_h": slot_h,
            }
            row_x += width + COL_GAP
            row_height = max(row_height, height)

        total_stack_height = row_y + row_height
        if layout_mode == "append_right":
            tech_top = segment_rules.get("tech_top", SEGMENT_PADDING_X)
        else:
            tech_top = max(existing_bottom + TECH_GAP_TOP, segment_height - total_stack_height - BOTTOM_MARGIN)
            tech_top = max(tech_top, TECH_GAP_TOP)

        content_bottom = tech_top + total_stack_height
        target_height = max(existing_bottom, content_bottom) + BOTTOM_MARGIN
        if target_height > segment_height:
            segment_geom.set("height", format_number(target_height))
            segment_height = target_height

        max_container_right = append_anchor
        placed_here = 0
        for label, group_items in groups.items():
            info = layout[label]
            group_id = f"tech_group_{slugify(segment_id + '_' + label)}"
            abs_x = info["rel_x"]
            abs_y = tech_top + info["rel_y"]
            add_container(
                root_cell,
                segment_id,
                group_id,
                label,
                abs_x,
                abs_y,
                info["width"],
                info["height"],
            )
            slot_w = info["slot_w"]
            slot_h = info["slot_h"]
            for item, (pos_x, pos_y) in zip(group_items, info["positions"]):
                geom = get_geometry(item["cell"])
                if geom is None:
                    continue
                offset_x = max(0.0, (slot_w - item["width"]) / 2)
                offset_y = max(0.0, (slot_h - item["height"]) / 2)
                geom.set("x", format_number(pos_x + offset_x))
                geom.set("y", format_number(pos_y + offset_y))
                item["cell"].set("parent", group_id)
                placed_here += 1
            max_container_right = max(max_container_right, abs_x + info["width"])

        neighbor_id = seg_data["neighbor"]
        if neighbor_id:
            neighbor_obj = objects_by_id.get(neighbor_id)
            if neighbor_obj is not None:
                neighbor_geom = get_geometry(neighbor_obj.find("mxCell"))
                neighbor_height = float_attr(neighbor_geom, "height")
                if segment_height > neighbor_height:
                    neighbor_geom.set("height", format_number(segment_height))

        max_needed_height = max(max_needed_height, segment_height)
        required_width = max(segment_width, max_container_right + SEGMENT_PADDING_RIGHT)
        if required_width > segment_width:
            segment_geom.set("width", format_number(required_width))
            segment_width = required_width
        stack_bottom = shift_stack_below(objects_by_id, segment_geom, segment_rules, SEGMENT_PADDING_X)
        max_needed_height = max(max_needed_height, stack_bottom)
        extent = shift_neighbor_chain(objects_by_id, segment_geom, segment_rules, SEGMENT_PADDING_X)
        dc_inner_extent = max(dc_inner_extent, extent + SEGMENT_PADDING_RIGHT)
        dc_inner_extent = max(dc_inner_extent, segment_x + segment_width + SEGMENT_PADDING_RIGHT)
        total_items += placed_here
        processed_segments += 1
        print(
            f"[{diagram_name}] [{segment_id}] Placed {placed_here} services across {len(groups)} groups; "
            f"segment height -> {format_number(segment_height)} px"
        )

    _, segments_extent, segments_bottom = get_segments_bounds(objects_by_id)
    dc_inner_extent = max(dc_inner_extent, segments_extent + SEGMENT_PADDING_RIGHT)
    max_needed_height = max(max_needed_height, segments_bottom)

    if dc_geom is not None:
        if max_needed_height > float_attr(dc_geom, "height"):
            dc_geom.set("height", format_number(max_needed_height))
        current_width = float_attr(dc_geom, "width")
        if dc_inner_extent > current_width:
            dc_geom.set("width", format_number(dc_inner_extent))

    result["total_items"] = total_items
    result["segments"] = processed_segments
    result["changed"] = total_items > 0
    if not result["changed"] and not result["reason"]:
        result["reason"] = "no services were placed after grouping"
    return result


def reflow_tech_services(args):
    tree = ET.parse(args.input)
    mxfile = tree.getroot()
    diagrams = resolve_target_diagrams(mxfile, args.diagram, args.diagram_filter)
    summary = []
    for diagram in diagrams:
        summary.append(process_diagram(diagram, args))

    if any(entry["changed"] for entry in summary):
        tree.write(args.input, encoding="utf-8", xml_declaration=True)

    for entry in summary:
        if entry["changed"]:
            print(
                f"[{entry['name']}] Total placed items: {entry['total_items']} "
                f"(segments: {entry['segments']})"
            )
        else:
            reason = entry["reason"] or "skipped without changes"
            print(f"[{entry['name']}] Skipped: {reason}")


def parse_args():
    parser = argparse.ArgumentParser(description="Layout technical services inside a DrawIO segment")
    parser.add_argument("-i", "--input", default="result/Sample_graph.drawio", help="DrawIO file to update")
    parser.add_argument("--diagram", default="all", help="Target diagram name or 'all'")
    parser.add_argument(
        "--diagram-filter",
        default="DC,ЦОД",
        help="Comma separated keywords for selecting diagrams when --diagram=all",
    )
    parser.add_argument(
        "--segment-id",
        default="",
        help="Fallback segment ID (???????????? ?????? ???? ?? ??????? ????????? ?????????????)",
    )
    parser.add_argument(
        "--neighbor-segment-id",
        default="",
        help="Fallback neighbor segment ID (??? ?????????????; ?????? ?? ?????)",
    )
    parser.add_argument(
        "--dc-container-id",
        default="001",
        help="ID of the outer DC container that bounds all segments",
    )
    return parser.parse_args()

if __name__ == "__main__":
    reflow_tech_services(parse_args())

