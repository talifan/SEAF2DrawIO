import xml.etree.ElementTree as ET
from typing import Optional, Any, Union

# Utility functions for XML manipulation (DrawIO specific)

def get_geometry(cell: Optional[ET.Element]) -> Optional[ET.Element]:
    """Retrieve mxGeometry element from an mxCell."""
    if cell is None:
        return None
    return cell.find("mxGeometry")

def float_attr(elem: Optional[ET.Element], key: str, default: float = 0.0) -> float:
    """Parse a float attribute from an XML element safely."""
    if elem is None:
        return default
    try:
        return float(elem.get(key, default))
    except (TypeError, ValueError):
        return default

def format_number(value: Union[float, int]) -> str:
    """Format a number for XML attributes (e.g., '10.5', '100')."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")

def find_diagram(mxfile_root: ET.Element, name: str) -> Optional[ET.Element]:
    """Find a diagram element by name."""
    for diagram in mxfile_root.findall("diagram"):
        if diagram.get("name") == name:
            return diagram
    return None

def parse_list_literal(raw_value: Any) -> list:
    """Safely parse a list literal from string or existing list."""
    if not raw_value:
        return []
    if isinstance(raw_value, (list, tuple, set)):
        return list(raw_value)
    if isinstance(raw_value, str):
        # Handle simple comma-separated or bracketed string
        import ast
        text = raw_value.strip()
        if text.startswith("[") or text.startswith("(") or text.startswith("{"):
            try:
                data = ast.literal_eval(text)
                if isinstance(data, (list, tuple, set)):
                    return list(data)
                return [data]
            except (ValueError, SyntaxError):
                pass
        # Fallback to comma split if not valid literal
        return [t.strip() for t in text.split(",") if t.strip()]
    return [raw_value]

def update_geometry(cell: ET.Element, **kwargs: float) -> None:
    """Update mxGeometry attributes efficiently."""
    geom = get_geometry(cell)
    if geom is None:
        return
    for k, v in kwargs.items():
        geom.set(k, format_number(v))
