import argparse
import sys
import os
import json

# Add project root to path to import lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.manual_drawio_parser import ManualDrawioParser
from lib.manual_drawio_classifier import ManualDrawioClassifier
from lib.manual_drawio_mapper import ManualDrawioMapper
from lib.manual_drawio_report import ManualDrawioReport
from lib.manual_drawio_validator import ManualDrawioValidator

def main():
    parser = argparse.ArgumentParser(description="Convert manual DrawIO schema to SEAF YAML")
    parser.add_argument("-s", "--src", required=True, help="Path to manual .drawio file")
    parser.add_argument("-o", "--out", default="result/manual_reverse", help="Output directory for YAML files")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.src):
        print(f"Error: File {args.src} not found")
        sys.exit(1)
        
    # Create output directory FIRST
    os.makedirs(args.out, exist_ok=True)
        
    print(f"Parsing {args.src}...")
    parser_obj = ManualDrawioParser(args.src)
    cells = parser_obj.parse()
    print(f"Extracted {len(cells)} cells.")
    
    # Save full cells for debugging
    with open(os.path.join(args.out, "parsed_nodes_full.json"), "w", encoding="utf-8") as f:
        json.dump(cells, f, indent=2, ensure_ascii=False)
    
    print("Classifying objects...")
    classifier = ManualDrawioClassifier(cells)
    classifier.classify_all()
    report = classifier.get_report()
    print(f"Classification report: {json.dumps(report, indent=2)}")
    
    print("Mapping to SEAF...")
    mapper = ManualDrawioMapper(classifier)
    mapper.map_all()
    
    print(f"Saving YAML files to {args.out}...")
    mapper.save_yaml(args.out)
    
    print("Generating report...")
    report_gen = ManualDrawioReport(classifier, mapper)
    report_gen.save(os.path.join(args.out, "summary_report.md"))
    
    print("Validating output...")
    validator = ManualDrawioValidator(args.out)
    validator.validate()
    print(validator.get_report())
    
    # Save a detailed recognition report
    report_path = os.path.join(args.out, "recognition_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        # Include more details in the report
        detailed_report = {
            'summary': report,
            'zones': [{'id': z['id'], 'title': z['value'], 'oid': z.get('seaf_oid')} for z in classifier.zones],
            'segments': [{'id': s['id'], 'title': s['value'], 'oid': s.get('seaf_oid'), 'parent': s.get('spatial_parent_value')} for s in classifier.segments]
        }
        json.dump(detailed_report, f, indent=2, ensure_ascii=False)
    
    print("Done!")

if __name__ == "__main__":
    main()
