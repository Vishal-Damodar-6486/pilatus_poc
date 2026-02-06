import os
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime

# --- CONFIGURATION ---
# os.environ["GOOGLE_API_KEY"] = "your-key-here"

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

def sanitize_for_pdf(text):
    """
    Injects a space after underscores in long strings.
    This allows the PDF engine to wrap the text instead of running off the page.
    """
    if isinstance(text, str):
        return text.replace("_", "_ ")
    return text

def generate_front_matter():
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    # We use Raw HTML for the tables to force specific column widths.
    # Markdown tables do not support width control.
    
    return f"""
# ENGINEERING REPORT

**Pilatus Aircraft Ltd.** Stans, Switzerland

<table style="width:100%; table-layout: fixed;">
    <col width="30%">
    <col width="70%">
    <tbody>
        <tr>
            <td><b>Affected Aircraft:</b></td>
            <td>PC-24</td>
        </tr>
        <tr>
            <td><b>Title:</b></td>
            <td><b>Automated Stress Analysis: Flap & Support Structure</b></td>
        </tr>
        <tr>
            <td><b>Report Number:</b></td>
            <td><b>ER-24-AUTO-001</b></td>
        </tr>
        <tr>
            <td><b>Issue:</b></td>
            <td>01</td>
        </tr>
        <tr>
            <td><b>Date:</b></td>
            <td>{date_str}</td>
        </tr>
        <tr>
            <td><b>Issuing Office:</b></td>
            <td>EXE</td>
        </tr>
    </tbody>
</table>

---

### PROPRIETARY NOTICE
This document contains Pilatus Aircraft Limited (in this document called Pilatus) proprietary information and shall at all times remain the property of Pilatus; no intellectual property right or licence is granted by Pilatus in connection with any information contained in it. It is supplied on the express condition that said information is treated as confidential, shall not be used for any purpose other than that for which it is supplied, shall not be disclosed in whole or in part, to third parties other than the Pilatus Group members and associated Partners, their subcontractors and suppliers (to the extent of their involvement in Pilatus projects), without Pilatus prior written consent.

---

### APPROVAL RECORD

<table style="width: 100%; table-layout: fixed; border-collapse: collapse; word-wrap: break-word; font-family: sans-serif;">
    <thead>
        <tr style="background-color: #f2f2f2;">
            <th style="width: 20%; border: 1px solid #ccc; padding: 8px; text-align: left;">Role</th>
            <th style="width: 40%; border: 1px solid #ccc; padding: 8px; text-align: left;">Name/Dept</th>
            <th style="width: 20%; border: 1px solid #ccc; padding: 8px; text-align: left;">Signature</th>
            <th style="width: 20%; border: 1px solid #ccc; padding: 8px; text-align: left;">Date</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="border: 1px solid #ccc; padding: 8px;"><b>Prepared by</b></td>
            <td style="border: 1px solid #ccc; padding: 8px;">Automated Engine (EXE)</td>
            <td style="border: 1px solid #ccc; padding: 8px;"><i>Signed</i></td>
            <td style="border: 1px solid #ccc; padding: 8px;">{date_str}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ccc; padding: 8px;"><b>Checked by</b></td>
            <td style="border: 1px solid #ccc; padding: 8px;">Senior Engineer (EXE)</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ccc; padding: 8px;"><b>Approved by</b></td>
            <td style="border: 1px solid #ccc; padding: 8px;">Head of Structure (EXE)</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ccc; padding: 8px;"><b>CVE M</b></td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
            <td style="border: 1px solid #ccc; padding: 8px;">&nbsp;</td>
        </tr>
    </tbody>
</table>

---
<div style="page-break-after: always;"></div>
"""

def generate_methodology():
    return """## 1. Introduction & Methodology
### 1.1 Scope
This report documents the structural substantiation of the Flap and Flap Support Structure for the PC-24 aircraft. The analysis covers static strength under critical flight loads.

### 1.2 Analysis Criteria
The structure is analyzed in accordance with **EASA CS-23** (Amendment 3).
* **Static Strength:** Compliance is shown by analysis (§23.305, §23.307).
* **Material Allowables:** A-Basis values are used for primary structure; B-Basis for redundant structure.
* **Fitting Factors:** A fitting factor of 1.15 is applied to all fittings and bearing checks (§23.625).

### 1.3 Tools & Methods
Internal loads were extracted from the Simcenter Nastran Finite Element Model (FEM). Margins of Safety (MS) and Reserve Factors (RF) were calculated using validated Pilatus Engineering Stress Sheets (PESS).
"""

def format_data_table(components_data, top_n=25):
    rows = []
    
    for name, data in components_data.items():
        if not data or not isinstance(data, dict): continue
        valid_cases = {k: v for k, v in data.items() if isinstance(v, dict) and 'RF' in v}
        if not valid_cases: continue
        
        crit_lc_id = min(valid_cases, key=lambda k: valid_cases[k]['RF'])
        crit_data = valid_cases[crit_lc_id]
        
        rows.append({
            "Component ID": sanitize_for_pdf(name), 
            "Load Case": crit_lc_id,
            "App. Load": float(crit_data.get('Applied_Load', 0)),
            "Allowable": float(crit_data.get('Allowable', 0)),
            "RF": float(crit_data.get('RF', 999.9)),
            "Failure Mode": crit_data.get('Failure_Mode', 'N/A')
        })
    
    if not rows: return "*(No valid results found)*"
    
    df = pd.DataFrame(rows)
    df_sorted = df.sort_values(by="RF", ascending=True).head(top_n)
    
    # Format Numbers
    df_sorted["App. Load"] = df_sorted["App. Load"].map('{:.1f}'.format)
    df_sorted["Allowable"] = df_sorted["Allowable"].map('{:.1f}'.format)
    df_sorted["RF"] = df_sorted["RF"].map('{:.2f}'.format)
    
    # We still use Markdown for the dynamic data tables because they vary in size
    # But xhtml2pdf usually handles 5+ columns better than 4 columns unless forced.
    return df_sorted.to_markdown(index=False)

def generate_chapter_assessment(chapter_name, components_data):
    llm = get_llm()
    
    total_count = 0
    fail_count = 0
    global_min_rf = 999.9
    critical_comp_name = ""
    critical_data = {}
    
    for name, data in components_data.items():
        if not data or not isinstance(data, dict): continue
        valid_rfs = [v['RF'] for k,v in data.items() if isinstance(v, dict) and 'RF' in v]
        if not valid_rfs: continue
        
        local_min = min(valid_rfs)
        total_count += 1
        if local_min < 1.0: fail_count += 1
        
        if local_min < global_min_rf:
            global_min_rf = local_min
            critical_comp_name = name
            lc_key = min(data, key=lambda k: data[k]['RF'] if isinstance(data[k], dict) else 999)
            critical_data = data[lc_key]

    if total_count == 0: return f"No valid analysis data found."

    system_instruction = """You are a Senior Stress Engineer at Pilatus writing a Certification Report (ER).
    Write a formal "Substantiation" paragraph.
    - Formal, technical, passive voice.
    - Reference specific failure modes (Shear, Buckling).
    - Be direct.
    """

    user_input = f"""
    Section: {chapter_name}
    Components Analyzed: {total_count}
    Failures (RF < 1.0): {fail_count}
    
    MOST CRITICAL COMPONENT:
    ID: {critical_comp_name}
    Min RF: {global_min_rf}
    Failure Mode: {critical_data.get('Failure_Mode', 'N/A')}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("human", user_input),
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({})

def generate_full_report_markdown(structured_results):
    md_report = generate_front_matter()
    md_report += generate_methodology()
    md_report += "\n---\n"
    
    md_report += "## 2. Summary of Results\n"
    md_report += "The minimum Reserve Factors (RF) for each major assembly are summarized below:\n\n"
    
    # IMPORTANT: No leading spaces before the <table tag
    md_report += """
<table style="width: 100%; table-layout: fixed; border-collapse: collapse; font-family: sans-serif;">
<thead>
<tr style="background-color: #f2f2f2;">
<th style="width: 30%; border: 1px solid #ccc; padding: 8px; text-align: left;">Component Group</th>
<th style="width: 40%; border: 1px solid #ccc; padding: 8px; text-align: left;">Critical Detail</th>
<th style="width: 15%; border: 1px solid #ccc; padding: 8px; text-align: left;">Min RF</th>
<th style="width: 15%; border: 1px solid #ccc; padding: 8px; text-align: left;">Compliance</th>
</tr>
</thead>
<tbody>
"""
    
    for chapter, components in structured_results.items():
        min_rf = 999.9
        crit_comp = "None"
        for name, data in components.items():
            valid_rfs = [v['RF'] for k,v in data.items() if isinstance(v, dict) and 'RF' in v]
            if valid_rfs:
                local_min = min(valid_rfs)
                if local_min < min_rf:
                    min_rf = local_min
                    crit_comp = name
        
        status = "COMPLIANT" if min_rf >= 1.0 else "NON-COMPLIANT"
        status_color = "#28a745" if status == "COMPLIANT" else "#dc3545"
        rf_display = f"{min_rf:.2f}" if min_rf != 999.9 else "N/A"
        
        # We use style="word-break: break-all;" to prevent long IDs from pushing the table
        md_report += f'<tr>'
        md_report += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle;">{chapter}</td>'
        md_report += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; word-break: break-all;">{sanitize_for_pdf(crit_comp)}</td>'
        md_report += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; text-align: center;"><b>{rf_display}</b></td>'
        md_report += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; text-align: center; color: {status_color};"><b>{status}</b></td>'
        md_report += f'</tr>'

    md_report += "</tbody></table>\n\n---\n"

    # ... rest of your code
    chapter_num = 3
    for chapter_name, components in structured_results.items():
        if not components: continue
        md_report += f"## {chapter_num}. {chapter_name} Substantiation\n"
        ai_text = f"{generate_chapter_assessment(chapter_name, components)}\n\n"
        print(ai_text)
        md_report += ai_text
        md_report += f"### {chapter_num}.1 Tabulated Margins\n"
        md_report += format_data_table(components, top_n=30) + "\n\n"
        chapter_num += 1
            
    return md_report