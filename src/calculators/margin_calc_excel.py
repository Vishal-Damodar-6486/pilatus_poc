import xlwings as xw
import json
import os

# --- CONFIGURATION ---
# NOTE: Ensure this path is correct on your machine
TARGET_EXCEL = r"C:\Users\VDAM4LZ2\PoC\pilatus_poc\inputs\excel\ER_24_000618_01_Upper_Panel_Analysis_Intact.xlsx"

def calculate_with_excel(json_data):
    """
    Drives the Excel spreadsheet using xlwings.
    """
    print(f"\n--- PHASE 2: EXCEL DRIVER ---")
    
    if not os.path.exists(TARGET_EXCEL):
        print(f"❌ Error: Excel file not found at {TARGET_EXCEL}")
        return {}

    results = json_data.get("Results", {})
    output_data = {"Elements": {}, "Freebodies": {}} # Structure to match API expectation

    app = xw.App(visible=True) 
    
    try:
        wb = app.books.open(TARGET_EXCEL)
        
        # --- SCENARIO: Upper Skin Panel Analysis ---
        if "Upper_Skin_Panel" in results.get("Elements", {}):
            sheet = wb.sheets['8'] 
            forces = results["Elements"]["Upper_Skin_Panel"]["Forces"]
            
            element_results = {}
            for lc_id, load in forces.items():
                if isinstance(load, str): continue
                
                print(f"Processing LC {lc_id} in Excel...")
                
                # 1. WRITE INPUTS 
                sheet.range('B33').value = load.get('Fx_Nmm', 0.0)
                sheet.range('C33').value = load.get('Fy_Nmm', 0.0)
                sheet.range('D33').value = load.get('Fxy_Nmm', 0.0)
                
                # 2. READ OUTPUTS
                rf_result = sheet.range('P33').value 
                
                status = "PASS"
                if rf_result is None: status = "ERROR"
                elif isinstance(rf_result, (int, float)) and rf_result <= 1.0: status = "FAIL"

                element_results[lc_id] = {
                    "Method": "Excel_Native",
                    "RF": rf_result,
                    "Status": status
                }
            
            output_data["Elements"]["Upper_Skin_Panel"] = element_results

    except Exception as e:
        print(f"❌ Excel Error: {e}")
    finally:
        try:
            wb.close()
            app.quit()
        except:
            pass
        
    return output_data