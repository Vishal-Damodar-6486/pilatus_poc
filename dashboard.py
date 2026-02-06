import streamlit as st
import requests
import pandas as pd
import altair as alt # Visualization library
import json
import base64  # <--- NEW IMPORT for PDF Display

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="PC-24 Stress Analysis", layout="wide")

st.title("✈️ PC-24 Automated Stress Analysis")
st.markdown("Upload your Solver Data (.op2) and Geometry Definitions (.dat) to generate certification reports.")

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.header("1. Upload Files")
    
    # A. Geometry Upload
    uploaded_dat = st.file_uploader("Geometry File (.dat)", type=["dat", "txt"])
    
    # B. Solver Upload
    uploaded_op2 = st.file_uploader("Solver File (.op2)", type=["op2"])
    
    st.header("2. Settings")
    calc_method = st.radio("Calculation Method", ["python", "excel"], index=0)
    
    load_cases_input = st.text_input("Load Cases (comma sep)", "1, 2, 3, 4, 5")
    load_cases = [int(x.strip()) for x in load_cases_input.split(",")]

# --- MAIN LOGIC ---

# 1. HANDLE DAT UPLOAD (Geometry)
if uploaded_dat is not None:
    if "current_dat" not in st.session_state or st.session_state["current_dat"] != uploaded_dat.name:
        with st.spinner("Parsing Geometry File..."):
            files = {"file": (uploaded_dat.name, uploaded_dat, "application/octet-stream")}
            try:
                response = requests.post(f"{API_BASE_URL}/upload/dat", files=files)
                if response.status_code == 200:
                    res_json = response.json()
                    st.success(f"✅ Parsed: {uploaded_dat.name}")
                    st.info(f"Found {res_json['components_found']} components.")
                    st.session_state["current_dat"] = uploaded_dat.name
                else:
                    st.error(f"DAT Parse failed: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

# 2. HANDLE OP2 UPLOAD (Solver)
if uploaded_op2 is not None:
    if "current_op2" not in st.session_state or st.session_state["current_op2"] != uploaded_op2.name:
        with st.spinner("Uploading Solver File..."):
            files = {"file": (uploaded_op2.name, uploaded_op2, "application/octet-stream")}
            try:
                response = requests.post(f"{API_BASE_URL}/upload/op2", files=files)
                if response.status_code == 200:
                    st.success(f"✅ Loaded: {uploaded_op2.name}")
                    st.session_state["current_op2"] = uploaded_op2.name
                else:
                    st.error(f"Upload failed: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

# 3. TRIGGER ANALYSIS
if uploaded_op2 and st.button("🚀 Run Stress Analysis"):
    payload = {
        "op2_filename": uploaded_op2.name,
        "calculation_method": calc_method,
        "load_cases": load_cases
    }
    
    with st.spinner("Extracting data & Calculating margins..."):
        try:
            response = requests.post(f"{API_BASE_URL}/analyze/full_report", json=payload)
            if response.status_code == 200:
                data = response.json()
                st.session_state["analysis_results"] = data["results"]
                st.success("Analysis Complete!")
            else:
                st.error(f"Analysis Failed: {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- DISPLAY RESULTS ---
if "analysis_results" in st.session_state:
    results = st.session_state["analysis_results"]
    
    # 1. Prepare Data for Visualization
    flat_rows = []
    # Iterate through groups (Elements/Freebodies)
    for group_type, components in results.items():
        if isinstance(components, dict):
            for comp_name, comp_data in components.items():
                if not isinstance(comp_data, dict): continue
                
                # Find worst case for this component
                min_rf = 999.9
                mode = "N/A"
                for lc, res in comp_data.items():
                    if isinstance(res, dict) and 'RF' in res:
                        # Ensure RF is a number
                        rf_val = res.get('RF')
                        if isinstance(rf_val, (int, float)) and rf_val < min_rf:
                            min_rf = rf_val
                            mode = res.get('Failure_Mode', 'N/A')
                
                if min_rf != 999.9:
                    flat_rows.append({
                        "Component": comp_name,
                        "Group": group_type,
                        "RF": min_rf,
                        "Failure Mode": mode,
                        "Status": "FAIL" if min_rf < 1.0 else "PASS"
                    })
    
    df = pd.DataFrame(flat_rows)
    
    if not df.empty:
        st.divider()
        st.header("📊 Executive Dashboard")
        
        # --- METRICS ROW ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Components", len(df))
        col2.metric("Critical Failures", len(df[df["RF"] < 1.0]))
        col3.metric("Min RF", f"{df['RF'].min():.2f}")
        col4.metric("Avg RF", f"{df['RF'].mean():.2f}")
        
        # --- CHARTS ROW ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("RF Distribution")
            hist_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X("RF", bin=alt.Bin(maxbins=20), title="Reserve Factor"),
                y='count()',
                color='Status'
            ).properties(height=300)
            st.altair_chart(hist_chart, use_container_width=True)
            
        with c2:
            st.subheader("Dominant Failure Modes")
            pie_chart = alt.Chart(df).mark_arc().encode(
                theta="count()",
                color="Failure Mode"
            ).properties(height=300)
            st.altair_chart(pie_chart, use_container_width=True)

        # --- CRITICAL ITEMS TABLE ---
        st.subheader("🚨 Critical Items (RF < 1.5)")
        # Filter for low RFs and sort
        critical_df = df[df["RF"] < 1.5].sort_values("RF").head(50)
        
        # Formatting for display
        st.dataframe(
            critical_df.style.format({"RF": "{:.2f}"})
            .applymap(lambda v: 'color: red; font-weight: bold' if isinstance(v, (int, float)) and v < 1.0 else '', subset=['RF']),
            use_container_width=True
        )

    # 4. GENERATE PDF REPORT
    st.divider()
    st.header("📝 Certification Report")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("📄 Generate PDF Report"):
            with st.spinner("Compiling PDF Report..."):
                try:
                    # Call the PDF endpoint
                    response = requests.post(
                        f"{API_BASE_URL}/generate/report_pdf", 
                        json={"analysis_results": results}
                    )
                    
                    if response.status_code == 200:
                        st.success("Report Generated Successfully!")
                        
                        # Store in Session State so it persists
                        st.session_state["pdf_data"] = response.content
                        
                    else:
                        st.error(f"Generation Failed: {response.text}")
                except Exception as e:
                     st.error(f"Error calling API: {e}")

    # DISPLAY PDF & DOWNLOAD BUTTON (Outside the button click logic)
    if "pdf_data" in st.session_state:
        pdf_bytes = st.session_state["pdf_data"]
        
        # 1. Encode PDF for Embedding
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # 2. Embed PDF Viewer (Iframe)
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 3. Download Button
        st.download_button(
            label="⬇️ Download Signed PDF", 
            data=pdf_bytes, 
            file_name="ER-24-AUTO-001_Stress_Report.pdf", 
            mime="application/pdf"
        )