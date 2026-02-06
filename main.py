from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import shutil
import os
import json
from typing import List, Dict, Any

# --- IMPORT LOCAL MODULES ---
from src.extractors.op2_reader import load_op2_file, extract_freebody_loads, extract_shell_forces
from src.calculators.margin_calc_python import calculate_panel_margins, calculate_joint_margins
from src.calculators.margin_calc_excel import calculate_with_excel
from src.generators.report_writer import generate_full_report_markdown

app = FastAPI(title="PC-24 Stress Analysis Automation API")

# --- CONFIGURATION ---
UPLOAD_DIR = "inputs/op2"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- CONFIG MAPPING ---
CONFIG_MAPPING = {
    "Freebodies": {
        "Front_Spar_Splice": {"id": 2710102} 
    },
    "Shell_Elements": {
        "Upper_Skin_Panel": {"id": 12090} 
    }
}

# --- Pydantic Models ---
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

@app.post("/upload/op2")
async def upload_op2(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        op2 = load_op2_file(file_path)
        if op2 is None:
             raise HTTPException(status_code=400, detail="Invalid OP2 file")
             
        available_lcs = []
        if hasattr(op2, 'cquad4_force'):
            # --- FIX: Convert numpy ints to python ints for JSON serialization ---
            available_lcs = [int(lc) for lc in op2.cquad4_force.keys()]
            
        return {
            "filename": file.filename,
            "status": "Uploaded Successfully",
            "available_load_cases": available_lcs[:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/full_report")
async def run_full_analysis(request: AnalysisRequest):
    op2_path = os.path.join(UPLOAD_DIR, request.op2_filename)
    if not os.path.exists(op2_path):
        raise HTTPException(status_code=404, detail="OP2 file not found.")

    # --- PHASE 1: EXTRACTION ---
    print(f"Loading {request.op2_filename}...")
    op2 = load_op2_file(op2_path)
    
    extracted_data = {"Results": {"Freebodies": {}, "Elements": {}}}
    
    for name, config in CONFIG_MAPPING["Freebodies"].items():
        extracted_data["Results"]["Freebodies"][name] = {
            "Loads": extract_freebody_loads(op2, config['id'], request.load_cases)
        }
        
    for name, config in CONFIG_MAPPING["Shell_Elements"].items():
        extracted_data["Results"]["Elements"][name] = {
            "Forces": extract_shell_forces(op2, config['id'], request.load_cases)
        }

    # --- PHASE 2: CALCULATION ---
    final_results = {"Elements": {}, "Freebodies": {}}
    
    if request.calculation_method == "python":
        # Python Mode: Calculate and sort into correct categories
        for name, data in extracted_data["Results"]["Elements"].items():
            final_results["Elements"][name] = calculate_panel_margins(name, data["Forces"])
            
        for name, data in extracted_data["Results"]["Freebodies"].items():
            final_results["Freebodies"][name] = calculate_joint_margins(name, data["Loads"])
            
    elif request.calculation_method == "excel":
        # Excel Mode
        final_results = calculate_with_excel(extracted_data)

    return {
        "status": "Analysis Complete",
        "method": request.calculation_method,
        "results": final_results
    }

@app.post("/generate/report")
async def create_narrative_report(request: ReportRequest):
    """
    Step 3: Feed the analysis numbers into GenAI to write the report.
    """
    try:
        # Call the LangChain module
        # We pass the 'results' dictionary which now has {"Elements":..., "Freebodies":...}
        markdown_text = generate_full_report_markdown(request.analysis_results)
        
        return {
            "status": "Report Generated",
            "format": "markdown",
            "content": markdown_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)