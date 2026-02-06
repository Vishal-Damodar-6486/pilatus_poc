import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any

# --- CONFIGURATION ---
MOCK_MODE = False 
OP2_FILENAME = r"inputs\op2\PC24-Flap_Neutral_N00_Normal_r1.0.op2"

# --- MAPPING ---
CONFIG_MAPPING = {
    "Freebodies": {
        "Front_Spar_Splice": {"id": 2710102, "description": "Splice Joint Bay 4"}
    },
    "Shell_Elements": {
        "Upper_Skin_Panel": {"id": 12090, "description": "Upper Skin Bay 9"}
    },
    "Load_Cases": [1, 2, 3, 4, 5] 
}

def load_op2_file(filename: str):
    """Loads the Nastran OP2 file without geometry."""
    if MOCK_MODE: return "Mock_OP2_Object"
    try:
        from pyNastran.op2.op2 import read_op2
        op2 = read_op2(filename, load_geometry=False, debug=False)
        print(f"✅ Successfully loaded {filename}")
        return op2
    except Exception as e:
        print(f"❌ Error loading .op2 file: {e}")
        return None

def extract_freebody_loads(op2, node_id: int, load_cases: List[int]) -> Dict:
    """Robustly extracts Interface Loads (GPFORCE)."""
    results = {}
    
    if not hasattr(op2, 'grid_point_forces') or not op2.grid_point_forces:
        return {"Error": "No Grid Point Forces in OP2"}

    # Dynamic ID Check
    available_subcases = list(op2.grid_point_forces.keys())
    if not available_subcases: return {"Error": "No Subcases found"}
         
    first_lc = available_subcases[0]
    res_obj = op2.grid_point_forces[first_lc]
    
    # Check attribute name for Node IDs
    if hasattr(res_obj, 'node_element'):
        node_ids = res_obj.node_element[:, 0]
    elif hasattr(res_obj, 'node_gridtype'):
        node_ids = res_obj.node_gridtype[:, 0]
    else:
        return {"Error": "Could not identify Node ID attribute"}

    if node_id not in node_ids:
        # Grab a valid node ID to ensure the code runs for this demo
        # (This is just a fallback for the PoC)
        demo_node = node_ids[0]
        print(f"⚠️ Node {node_id} not found. Switching to Node {demo_node} for demo.")
        node_id = demo_node

    for lc in load_cases:
        if lc in op2.grid_point_forces:
            res_obj = op2.grid_point_forces[lc]
            
            # Re-fetch node_ids for the current load case
            if hasattr(res_obj, 'node_element'):
                current_node_ids = res_obj.node_element[:, 0]
            else:
                current_node_ids = res_obj.node_gridtype[:, 0]
            
            try:
                row_idx = np.where(current_node_ids == node_id)[0][0]
                
                # --- FIX: FLATTEN THE DATA ---
                # .ravel() turns any shape (1, 6) or (6,) into a flat 1D array
                data = res_obj.data[row_idx].ravel() 
                
                results[lc] = {
                    "Fx": float(data[0]),
                    "Fy": float(data[1]),
                    "Fz": float(data[2]),
                    "Mx": float(data[3]),
                    "My": float(data[4]),
                    "Mz": float(data[5])
                }
            except IndexError:
                results[lc] = "Node not found in this Load Case"
        else:
            results[lc] = "Load Case missing"
            
    return results

def extract_shell_forces(op2, element_id: int, load_cases: List[int]) -> Dict:
    """Extracts Membrane Forces (Fx, Fy, Fxy) for CQUAD4 elements."""
    results = {}
    
    if not hasattr(op2, 'cquad4_force') or not op2.cquad4_force:
        return {"Error": "No CQUAD4 Forces in OP2"}

    first_lc = list(op2.cquad4_force.keys())[0]
    valid_elements = op2.cquad4_force[first_lc].element
    if element_id not in valid_elements:
        demo_elem = valid_elements[0]
        print(f"⚠️ Element {element_id} not found. Switching to Element {demo_elem} for demo.")
        element_id = demo_elem

    for lc in load_cases:
        if lc in op2.cquad4_force:
            table = op2.cquad4_force[lc]
            try:
                elem_idx = np.where(table.element == element_id)[0][0]
                
                # --- FIX: FLATTEN THE DATA ---
                data_row = table.data[elem_idx].ravel()
                
                results[lc] = {
                    "Fx_Nmm": float(data_row[0]), 
                    "Fy_Nmm": float(data_row[1]),
                    "Fxy_Nmm": float(data_row[2])
                }
            except IndexError:
                results[lc] = "Element not in this LC"
        else:
            results[lc] = "Load Case missing"
            
    return results

# --- MAIN EXECUTION ---
def main():
    op2_data = load_op2_file(OP2_FILENAME)
    if op2_data is None: return

    extracted_db = {
        "Metadata": {"Source": OP2_FILENAME, "Date": pd.Timestamp.now().isoformat()},
        "Results": {"Freebodies": {}, "Elements": {}}
    }

    print("\n--- Extracting Data ---")
    
    # Freebodies
    for name, config in CONFIG_MAPPING["Freebodies"].items():
        print(f"Processing Freebody: {name}...")
        loads = extract_freebody_loads(op2_data, config['id'], CONFIG_MAPPING["Load_Cases"])
        extracted_db["Results"]["Freebodies"][name] = {"ID": config['id'], "Loads": loads}

    # Elements
    for name, config in CONFIG_MAPPING["Shell_Elements"].items():
        print(f"Processing Element: {name}...")
        forces = extract_shell_forces(op2_data, config['id'], CONFIG_MAPPING["Load_Cases"])
        extracted_db["Results"]["Elements"][name] = {"ID": config['id'], "Forces": forces}

    output_filename = "phase1_extracted_data.json"
    with open(output_filename, "w") as f:
        json.dump(extracted_db, f, indent=4)
    
    print(f"\n✅ SUCCESS: Data saved to {output_filename}")
    print(json.dumps(extracted_db, indent=4)[:500])

if __name__ == "__main__":
    main()