import subprocess
import os
import sys
import yaml

def run_regression_test():
    print("Running regression test for manual_drawio_to_seaf.py...")
    src_file = "result/Draft. Новый шаблон Р41 - Схема функциональной сетевой архитектуры v1.2 20231124_01 (2).drawio"
    out_dir = "P41_to_yaml/tz/output_test"
    
    if not os.path.exists(src_file):
        print(f"Source file {src_file} not found. Skipping test.")
        sys.exit(0)
        
    # Step 1: Convert
    cmd = ["python3", "P41_to_yaml/scripts/manual_drawio_to_seaf.py", "-s", src_file, "-o", out_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Conversion failed:\n{result.stdout}\n{result.stderr}")
        sys.exit(1)
    
    # Step 2: Validate YAMLs
    full_yaml = os.path.join(out_dir, "seaf_full.yaml")
    if not os.path.exists(full_yaml):
        print("❌ seaf_full.yaml not found.")
        sys.exit(1)
        
    # We don't run seaf2drawio.py here because it requires Python 3.10+ and 
    # we are not allowed to change it. 
    # But we can verify the YAML content against our Quality Gates.
    
    with open(full_yaml, 'r') as f:
        data = yaml.safe_load(f)
        
    checks = [
        (len(data.get('seaf.company.ta.services.network_segments', {})) >= 22, "Expected 22+ segments"),
        (len(data.get('seaf.company.ta.services.networks', {})) >= 70, "Expected 70+ networks"),
        (len(data.get('seaf.company.ta.components.networks', {})) >= 120, "Expected 120+ components"),
        ('project.dc_region.auto_created' in data.get('seaf.company.ta.services.dc_regions', {}), "Region auto-created"),
        ('project.dc_az.auto_created' in data.get('seaf.company.ta.services.dc_azs', {}), "AZ auto-created"),
    ]
    
    failed = False
    for passed, msg in checks:
        if not passed:
            print(f"❌ Quality Gate Failed: {msg}")
            failed = True
        else:
            print(f"✅ Quality Gate Passed: {msg}")
            
    if failed:
        sys.exit(1)
    else:
        print("✅ All internal Quality Gates passed.")

if __name__ == "__main__":
    run_regression_test()
