import json
import html

def parse_mxlibrary(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('<mxlibrary>', '').replace('</mxlibrary>', '')
    return json.loads(json_str)

def main():
    before = parse_mxlibrary('data/Избранное_P41_before.xml')
    after = parse_mxlibrary('data/Избранное_P41_after.xml')
    
    for item in before:
        if item.get('title') == 'AntiVirus':
            print("BEFORE AntiVirus XML:")
            print(html.unescape(item['xml']))
            break
            
    for item in after:
        if item.get('title') == 'AntiVirus':
            print("\nAFTER AntiVirus XML:")
            print(html.unescape(item['xml']))
            break

if __name__ == "__main__":
    main()
