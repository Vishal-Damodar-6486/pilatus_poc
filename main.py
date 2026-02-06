from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import shutil
import os
import json
from typing import List, Dict, Any

# --- IMPORT LOCAL MODULES ---
from src.extractors.op2_reader import load_op2_file, extract_freebody_loads, extract_shell_forces, load_mapping
from src.extractors.dat_parser import parse_dat_mapping 
from src.calculators.margin_calc_python import calculate_panel_margins, calculate_joint_margins
from src.calculators.margin_calc_excel import calculate_with_excel
from src.generators.report_writer import generate_full_report_markdown
from src.extractors.result_organizer import organize_results_into_chapters 
from fastapi.responses import Response 
from src.generators.pdf_converter import convert_markdown_to_pdf 

app = FastAPI(title="PC-24 Stress Analysis Automation API")

# --- CONFIGURATION ---
INPUT_DIR = "inputs"
OUTPUT_DIR = "outputs"
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- MODELS ---
class AnalysisRequest(BaseModel):
    op2_filename: str
    calculation_method: str = "python"
    load_cases: List[int] = [1, 2, 3, 4, 5]

class ReportRequest(BaseModel):
    analysis_results: Dict[str, Any] 

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Stress Analysis Engine Ready."}

@app.post("/upload/dat")
async def upload_dat(file: UploadFile = File(...)):
    """
    Uploads a Nastran .dat file, parses it for group definitions,
    and saves the 'model_mapping.json' for the analysis engine.
    """
    file_path = os.path.join(INPUT_DIR, file.filename)
    try:
        # 1. Save File
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Trigger Parser
        print(f"Parsing Geometry from {file.filename}...")
        mapping = parse_dat_mapping(file_path)
        
        if not mapping:
            raise HTTPException(status_code=400, detail="Could not parse any groups from .dat file")

        # 3. Save Mapping JSON
        with open("src/extractors/model_mapping.json", "w") as f:
            json.dump(mapping, f, indent=4)

        return {
            "filename": file.filename,
            "status": "Parsed Successfully",
            "components_found": len(mapping),
            "groups": list(mapping.keys())[:5] 
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/op2")
async def upload_op2(file: UploadFile = File(...)):
    file_path = os.path.join(INPUT_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        op2 = load_op2_file(file_path)
        if op2 is None:
             raise HTTPException(status_code=400, detail="Invalid OP2 file")
             
        available_lcs = []
        if hasattr(op2, 'cquad4_force'):
            available_lcs = [int(k) for k in list(op2.cquad4_force.keys())]
            
        return {
            "filename": file.filename,
            "status": "Uploaded Successfully",
            "available_load_cases": available_lcs[:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/full_report")
async def run_full_analysis(request: AnalysisRequest):
    op2_path = os.path.join(INPUT_DIR, request.op2_filename)
    if not os.path.exists(op2_path):
        raise HTTPException(status_code=404, detail="OP2 file not found.")

    print(f"Loading {request.op2_filename}...")
    op2 = load_op2_file(op2_path)
    
    # --- PHASE 1: EXTRACTION ---
    mapping_data = load_mapping()
    
    if not mapping_data:
        print("⚠️ No mapping found. Using fallback demo mapping.")
        mapping_data = {
            "Upper_Skin_Panel": {"ids": [12090], "type": "panel"},
            "Intermediate_Ribs": {"ids": [2710102], "type": "freebody"}
        }

    extracted_data = {"Results": {"Freebodies": {}, "Elements": {}}}
    
    for name, info in mapping_data.items():
        if not info.get('ids'): continue
        target_id = info['ids'][0]
        
        if "panel" in name.lower() or "skin" in name.lower() or "clip" in name.lower():
             extracted_data["Results"]["Elements"][name] = {
                "Forces": extract_shell_forces(op2, target_id, request.load_cases)
            }
        else:
             extracted_data["Results"]["Freebodies"][name] = {
                "Loads": extract_freebody_loads(op2, target_id, request.load_cases)
            }

    # --- PHASE 2: CALCULATION ---
    final_results = {"Elements": {}, "Freebodies": {}}
    
    if request.calculation_method == "python":
        for name, data in extracted_data["Results"]["Elements"].items():
            final_results["Elements"][name] = calculate_panel_margins(name, data["Forces"])
        for name, data in extracted_data["Results"]["Freebodies"].items():
            final_results["Freebodies"][name] = calculate_joint_margins(name, data["Loads"])
            
    elif request.calculation_method == "excel":
        final_results = calculate_with_excel(extracted_data)

    # --- STEP 3: SAVE RESULTS TO FILE ---
    # This ensures we have a permanent record of the Phase 2 output
    output_filename = f"phase2_results_{request.calculation_method}.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        with open(output_path, "w") as f:
            json.dump(final_results, f, indent=4)
        print(f"💾 Results saved to {output_path}")
    except Exception as e:
        print(f"⚠️ Failed to save output file: {e}")

    return {
        "status": "Analysis Complete",
        "method": request.calculation_method,
        "saved_to": output_path,
        "results": final_results
    }

    
@app.post("/generate/report_pdf")
async def create_pdf_report(request: ReportRequest):
    try:
        # 1. Organize Data (The Librarian)
        structured_data = organize_results_into_chapters(request.analysis_results)
        
        # 2. Generate Markdown (The Writer)
        markdown_text = generate_full_report_markdown(structured_data)
        
        # 3. Convert to PDF (The Printer)
        pdf_bytes = convert_markdown_to_pdf(markdown_text)
        
        # 4. Return Binary Stream
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Certification_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)