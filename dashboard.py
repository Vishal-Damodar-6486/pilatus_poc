import streamlit as st
import requests
import pandas as pd
import json

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="PC-24 Stress Analysis", layout="wide")

st.title("✈️ PC-24 Automated Stress Analysis")
st.markdown("Upload a solver file (.op2) to generate certification reports.")

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.header("1. Upload Solver File")
    uploaded_file = st.file_uploader("Choose a Nastran .op2 file", type=["op2"])
    
    st.header("2. Settings")
    calc_method = st.radio("Calculation Method", ["python", "excel"], index=0)
    
    load_cases_input = st.text_input("Load Cases (comma sep)", "1, 2, 3, 4, 5")
    load_cases = [int(x.strip()) for x in load_cases_input.split(",")]

# --- MAIN LOGIC ---

# 1. HANDLE UPLOAD
if uploaded_file is not None:
    # Check if file is already uploaded to avoid re-posting on every refresh
    if "current_file" not in st.session_state or st.session_state["current_file"] != uploaded_file.name:
        with st.spinner("Uploading to Analysis Engine..."):
            files = {"file": (uploaded_file.name, uploaded_file, "application/octet-stream")}
            try:
                response = requests.post(f"{API_BASE_URL}/upload/op2", files=files)
                if response.status_code == 200:
                    st.success(f"✅ Loaded: {uploaded_file.name}")
                    st.json(response.json()) # Show available load cases
                    st.session_state["current_file"] = uploaded_file.name
                else:
                    st.error(f"Upload failed: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to API. Is 'uvicorn main:app' running?")

    # 2. TRIGGER ANALYSIS
    if st.button("🚀 Run Stress Analysis"):
        payload = {
            "op2_filename": uploaded_file.name,
            "calculation_method": calc_method,
            "load_cases": load_cases
        }
        
        with st.spinner("Extracting data & Calculating margins..."):
            try:
                response = requests.post(f"{API_BASE_URL}/analyze/full_report", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["analysis_results"] = data["results"] # Save for next step
                    st.success("Analysis Complete!")
                else:
                    st.error(f"Analysis Failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# --- DISPLAY RESULTS ---
if "analysis_results" in st.session_state:
    results = st.session_state["analysis_results"]
    
    st.divider()
    st.header("📊 Phase 2: Calculation Results")
    
    # Flatten JSON for Table Display
    table_rows = []
    
    # Process Elements
    for component, cases in results.get("Elements", {}).items():
        for lc, data in cases.items():
            if isinstance(data, dict):
                row = {"Type": "Panel", "Component": component, "Load Case": lc}
                row.update(data) # Adds RF, Failure_Mode, etc.
                table_rows.append(row)
                
    # Process Freebodies
    for component, cases in results.get("Freebodies", {}).items():
        for lc, data in cases.items():
             if isinstance(data, dict):
                row = {"Type": "Joint", "Component": component, "Load Case": lc}
                row.update(data)
                table_rows.append(row)
    
    if table_rows:
        df = pd.DataFrame(table_rows)
        
        # Color coding function
        def highlight_rf(val):
            color = 'red' if val < 1.0 else 'green'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df.style.applymap(highlight_rf, subset=['RF'])
            .format({"RF": "{:.2f}", "Applied_Load": "{:.1f}", "Allowable": "{:.1f}"}),
            use_container_width=True
        )
    
    # 3. TRIGGER GENAI REPORT
    st.divider()
    st.header("📝 Phase 3: AI Report Generation")
    
    if st.button("🤖 Write Certification Report"):
        payload = {"analysis_results": results}
        
        with st.spinner("Consulting Gemini..."):
            try:
                response = requests.post(f"{API_BASE_URL}/generate/report", json=payload)
                if response.status_code == 200:
                    report_content = response.json()["content"]
                    st.markdown(report_content)
                    
                    # Download Button
                    st.download_button(
                        label="📄 Download Report as Markdown",
                        data=report_content,
                        file_name="Automated_Stress_Report.md",
                        mime="text/markdown"
                    )
                else:
                    st.error(f"Generation Failed: {response.text}")
            except Exception as e:
                 st.error(f"Error calling AI: {e}")