import json
import re
import html

def parse_mxlibrary(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('<mxlibrary>', '').replace('</mxlibrary>', '')
    return json.loads(json_str)

def get_object_fields(xml_str):
    # Unescape twice if necessary
    s = html.unescape(xml_str)
    # Match <object ...>
    match = re.search(r'<object\s+(.*?)>', s, re.DOTALL)
    if not match:
        return None
    
    attr_str = match.group(1)
    # Simple regex to find key="value"
    attrs = {}
    for m in re.finditer(r'(\w+)="([^"]*)"', attr_str):
        attrs[m.group(1)] = m.group(2)
    return attrs

def main():
    before = parse_mxlibrary('data/Избранное_P41_before.xml')
    after = parse_mxlibrary('data/Избранное_P41_after.xml')
    
    before_map = {item.get('title') or f"Item_{i}": item for i, item in enumerate(before)}
    after_map = {item.get('title') or f"Item_{i}": item for i, item in enumerate(after)}
    
    all_titles = set(before_map.keys()) | set(after_map.keys())
    
    print(f"{'Stencil Title':<30} | Status | Changes")
    print("-" * 80)
    
    for title in sorted(all_titles):
        b_item = before_map.get(title)
        a_item = after_map.get(title)
        
        if not b_item:
            print(f"{title:<30} | NEW    |")
            continue
        if not a_item:
            print(f"{title:<30} | REMOVED|")
            continue
            
        b_fields = get_object_fields(b_item['xml'])
        a_fields = get_object_fields(a_item['xml'])
        
        if b_fields != a_fields:
            if b_fields is None or a_fields is None:
                print(f"{title:<30} | CHANGED| Object tag presence changed")
                continue
                
            b_keys = set(b_fields.keys())
            a_keys = set(a_fields.keys())
            
            added = a_keys - b_keys
            removed = b_keys - a_keys
            changed = {k for k in (b_keys & a_keys) if b_fields[k] != a_fields[k]}
            
            diffs = []
            if added: diffs.append(f"Added: {added}")
            if removed: diffs.append(f"Removed: {removed}")
            for k in changed:
                diffs.append(f"'{k}': '{b_fields[k]}' -> '{a_fields[k]}'")
            
            print(f"{title:<30} | CHANGED| {'; '.join(diffs)}")

if __name__ == "__main__":
    main()
