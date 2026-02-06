import math

# --- CONFIGURATION ---
# In production, this should ideally be loaded from a config file
ALLOWABLES = {
    "Upper_Skin_Panel": {
        "Shear_Allowable": 28.56,  # N/mm
        "Compression_Allowable": 26.03 # N/mm
    },
    "Front_Spar_Splice": {
        "Joint_Shear_Allowable": 1334.0, # N
        "Bearing_Allowable": 2500.0 # N
    }
}

def calculate_panel_margins(element_name, loads):
    """
    Python-native calculation for Panel Stability (Buckling).
    """
    analysis_results = {}
    
    # Get Allowables
    allow_comp = ALLOWABLES.get(element_name, {}).get("Compression_Allowable", 20.0)
    allow_shear = ALLOWABLES.get(element_name, {}).get("Shear_Allowable", 20.0)

    for lc, forces in loads.items():
        if isinstance(forces, str): continue 
        
        fx = abs(forces.get("Fx_Nmm", 0.0))
        fxy = abs(forces.get("Fxy_Nmm", 0.0))
        
        # Calculate RFs (Avoid division by zero)
        rf_comp = allow_comp / fx if fx > 1e-6 else 99.99
        rf_shear = allow_shear / fxy if fxy > 1e-6 else 99.99
        
        if rf_comp < rf_shear:
            critical_rf = rf_comp
            mode = "Compression"
        else:
            critical_rf = rf_shear
            mode = "Shear"
            
        analysis_results[lc] = {
            "Method": "Python_Fast",
            "Applied_Load": max(fx, fxy),
            "Allowable": allow_comp if mode == "Compression" else allow_shear,
            "RF": round(critical_rf, 2),
            "Failure_Mode": mode
        }
    return analysis_results

def calculate_joint_margins(freebody_name, loads):
    """
    Python-native calculation for Joint Strength.
    """
    analysis_results = {}
    
    # Get Allowables
    allowable = ALLOWABLES.get(freebody_name, {}).get("Joint_Shear_Allowable", 1000.0)

    for lc, forces in loads.items():
        if isinstance(forces, str): continue
        
        fx = forces.get("Fx", 0.0)
        fy = forces.get("Fy", 0.0)
        fz = forces.get("Fz", 0.0)
        resultant_force = math.sqrt(fx**2 + fy**2 + fz**2)
        
        rf = allowable / resultant_force if resultant_force > 1e-6 else 99.99
        
        analysis_results[lc] = {
            "Method": "Python_Fast",
            "Applied_Load": round(resultant_force, 2),
            "Allowable": allowable,
            "RF": round(rf, 2),
            "Failure_Mode": "Resultant Shear"
        }
    return analysis_results