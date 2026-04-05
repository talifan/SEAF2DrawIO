import xml.etree.ElementTree as ET
import base64
import zlib
import urllib.parse
import json
import os
import re

class ManualDrawioParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.cells = []
        self.diagrams = []

    def decompress_diagram(self, data):
        """Decompress a draw.io diagram (base64 -> deflate -> url-decode)."""
        try:
            compressed = base64.b64decode(data)
            decompressed = zlib.decompress(compressed, -15)
            return urllib.parse.unquote(decompressed.decode('utf-8'))
        except Exception:
            return data

    def parse(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        
        for diagram_tag in root.findall('diagram'):
            data = diagram_tag.text
            if data:
                xml_str = self.decompress_diagram(data)
                diagram_root = ET.fromstring(xml_str)
                self.diagrams.append({
                    'name': diagram_tag.get('name'),
                    'root': diagram_root
                })
            else:
                mxgraphmodel = diagram_tag.find('mxGraphModel')
                if mxgraphmodel is not None:
                    self.diagrams.append({
                        'name': diagram_tag.get('name'),
                        'root': mxgraphmodel
                    })

        all_cells = []
        for diag in self.diagrams:
            cells = self._extract_cells(diag['root'])
            # Add diagram name to each cell for context
            for c in cells:
                c['diagram_name'] = diag['name']
            all_cells.extend(cells)
        
        self.cells = all_cells
        
        # Post-process: Calculate absolute coordinates
        self._calculate_absolute_coordinates()
        
        return self.cells

    def _calculate_absolute_coordinates(self):
        """Calculate absolute x, y by traversing parents."""
        cell_dict = {c['id']: c for c in self.cells}
        
        def get_abs_pos(cell_id):
            cell = cell_dict.get(cell_id)
            if not cell or not cell.get('geometry'):
                return 0, 0
            
            parent_id = cell.get('parent')
            # 0 and 1 are special roots in DrawIO, their children are at absolute positions
            if parent_id in ['0', '1'] or parent_id is None:
                return cell['geometry']['x'], cell['geometry']['y']
            
            px, py = get_abs_pos(parent_id)
            return px + cell['geometry']['x'], py + cell['geometry']['y']

        for cell in self.cells:
            if cell.get('vertex') and cell.get('geometry'):
                ax, ay = get_abs_pos(cell['id'])
                cell['abs_x'] = ax
                cell['abs_y'] = ay
            elif cell.get('edge') and cell.get('geometry'):
                # For edges, we might need to adjust source/target points if they are relative to parents
                # But edges in manual diagrams often have absolute sourcePoint/targetPoint
                pass

    def _clean_html(self, text):
        if not text: return ""
        # Replace common block/break tags with spaces to avoid gluing words
        clean = re.sub(r'<(br|p|div|li)[^>]*>', ' ', text, flags=re.IGNORECASE)
        # Remove all other HTML tags
        clean = re.sub(r'<[^<]+?>', '', clean)
        # Unescape XML/HTML entities
        import html
        clean = html.unescape(clean)
        # Clean extra whitespace
        clean = ' '.join(clean.split())
        return clean

    def _extract_cells(self, diagram_root):
        cells = []
        root_node = diagram_root.find('root')
        if root_node is None:
            root_node = diagram_root

        # Process mxCell
        for cell in root_node.findall('mxCell'):
            cells.append(self._parse_cell_element(cell))
            
        # Process object and UserObject (often contain metadata)
        for obj_tag in ['object', 'UserObject']:
            for obj in root_node.findall(obj_tag):
                cell = obj.find('mxCell')
                if cell is not None:
                    cell_data = self._parse_cell_element(cell)
                    # Attributes of the wrapper tag override mxCell attributes and provide metadata
                    cell_data['id'] = obj.get('id', cell_data['id'])
                    cell_data['value'] = obj.get('label', obj.get('value', cell_data['value']))
                    
                    # Store all attributes as metadata
                    metadata = {k: v for k, v in obj.attrib.items() if k not in ['id', 'label', 'value']}
                    if 'metadata' in cell_data:
                        cell_data['metadata'].update(metadata)
                    else:
                        cell_data['metadata'] = metadata
                    cells.append(cell_data)

        # Post-process: clean labels
        for c in cells:
            c['raw_value'] = c['value']
            c['value'] = self._clean_html(c['value'])

        return cells

    def _parse_cell_element(self, cell):
        cell_data = {
            'id': cell.get('id'),
            'parent': cell.get('parent'),
            'style': cell.get('style', ''),
            'value': cell.get('value', ''),
            'edge': cell.get('edge') == "1",
            'source': cell.get('source'),
            'target': cell.get('target'),
            'vertex': cell.get('vertex') == "1"
        }
        
        geometry = cell.find('mxGeometry')
        if geometry is not None:
            cell_data['geometry'] = {
                'x': float(geometry.get('x', 0)) if geometry.get('x') else 0,
                'y': float(geometry.get('y', 0)) if geometry.get('y') else 0,
                'width': float(geometry.get('width', 0)) if geometry.get('width') else 0,
                'height': float(geometry.get('height', 0)) if geometry.get('height') else 0
            }
            # Handle points for edges
            source_pt = geometry.find("mxPoint[@as='sourcePoint']")
            target_pt = geometry.find("mxPoint[@as='targetPoint']")
            if source_pt is not None:
                cell_data['geometry']['sourcePoint'] = {
                    'x': float(source_pt.get('x', 0)),
                    'y': float(source_pt.get('y', 0))
                }
            if target_pt is not None:
                cell_data['geometry']['targetPoint'] = {
                    'x': float(target_pt.get('x', 0)),
                    'y': float(target_pt.get('y', 0))
                }
        return cell_data

    def get_style_param(self, style, param):
        if not style: return None
        parts = style.split(';')
        for p in parts:
            if p.startswith(param + '='):
                return p.split('=')[1]
        return None
