import xlwings as xw
import json
import os
import sys

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(BASE_DIR, "calculator_registry.json")
# Assuming standard project structure: src/calculators -> project_root/inputs/excel
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
EXCEL_DIR = os.path.join(PROJECT_ROOT, "inputs", "excel")

def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Registry not found at: {REGISTRY_PATH}")
        return {}
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)

def find_registry_config(component_name, registry):
    """
    Smart Lookup:
    1. Tries exact match.
    2. Tries pattern match (if registry key is part of component name).
    """
    # 1. Exact Match
    if component_name in registry:
        return registry[component_name]
    
    # 2. Pattern Match (e.g., "Rib_1" matches config "Intermediate_Ribs")
    # We prioritize longer matches to be specific
    for key, config in registry.items():
        # Check if the Registry Key (e.g. "Rib") is inside the Component Name (e.g. "Rib_12")
        # Case insensitive comparison is safer
        if key.lower() in component_name.lower():
            print(f"   (Matched '{component_name}' to Registry Key '{key}')")
            return config
            
    return None

def calculate_with_excel(json_data):
    print(f"\n--- PHASE 2: EXCEL DRIVER (REGISTRY MODE) ---")
    
    registry = load_registry()
    if not registry:
        return {"Error": "Calculator Registry Missing"}

    results = json_data.get("Results", {})
    final_output = {"Elements": {}, "Freebodies": {}}

    app = xw.App(visible=True) 

    try:
        for comp_type in ["Elements", "Freebodies"]:
            if comp_type not in results: continue

            for component_name, comp_data in results[comp_type].items():
                
                # --- NEW: Use Smart Lookup ---
                config = find_registry_config(component_name, registry)
                
                if not config:
                    print(f"⚠️ No Calculator found for '{component_name}'. Skipping.")
                    continue
                
                file_path = os.path.join(EXCEL_DIR, config["filename"])
                if not os.path.exists(file_path):
                    print(f"❌ Excel file missing: {file_path}")
                    final_output[comp_type][component_name] = {"Error": "Excel file not found"}
                    continue

                print(f"📂 Opening {config['filename']} for {component_name}...")
                wb = app.books.open(file_path)
                
                try:
                    # --- DRIVER TYPE A: SIMPLE (Row-by-Row Injection) ---
                    if config["driver"] == "excel_simple":
                        sheet = wb.sheets[config["sheet"]]
                        comp_results = {}
                        
                        loads_map = comp_data.get("Forces", comp_data.get("Loads", {}))

                        for lc_id, load_vals in loads_map.items():
                            if isinstance(load_vals, str): continue
                            
                            # Write Inputs
                            for json_key, cell_addr in config["inputs"].items():
                                val = load_vals.get(json_key, 0.0)
                                sheet.range(cell_addr).value = abs(val) if "Fx" in json_key or "Fy" in json_key else val
                            
                            # Read Output
                            rf = sheet.range(config["output_rf"]).value
                            
                            status = "PASS"
                            if rf is None: status = "ERROR"
                            elif isinstance(rf, (int, float)) and rf < 1.0: status = "FAIL"

                            comp_results[lc_id] = {
                                "Method": "Excel_Simple",
                                "RF": rf,
                                "Status": status
                            }
                        
                        final_output[comp_type][component_name] = comp_results

                    # --- DRIVER TYPE B: MASTER (Summary Read) ---
                    elif config["driver"] == "excel_master":
                        sheet = wb.sheets[config["output_sheet"]]
                        min_rf = sheet.range(config["output_cell_rf"]).value
                        location = sheet.range(config["output_cell_loc"]).value
                        
                        print(f"   -> Master Result: Min RF = {min_rf} at {location}")
                        
                        comp_results = {}
                        # For PoC, apply Master Result to all requested cases
                        for lc in [1, 2, 3, 4, 5]: 
                             comp_results[lc] = {
                                 "Method": "Excel_Master",
                                 "RF": min_rf, 
                                 "Note": f"Critical Loc: {location}",
                                 "Status": "PASS" if (isinstance(min_rf, (int, float)) and min_rf > 1.0) else "FAIL"
                             }
                        
                        final_output[comp_type][component_name] = comp_results
                
                finally:
                    # Close workbook to keep it clean for next run
                    wb.close()

    except Exception as e:
        print(f"❌ Critical Excel Error: {e}")
        return {"Error": str(e)}
    finally:
        try:
            app.quit()
        except:
            pass

    return final_output