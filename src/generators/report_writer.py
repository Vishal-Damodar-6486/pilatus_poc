import re
import os
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
from src.generators.chart_generator import generate_rf_chart

def generate_table_of_figures(md_content):
    """
    Scans the markdown content for Figure captions and generates a Table of Figures.
    Assumes captions format: *Figure X.Y: Caption*
    """
    # Regex to find: <a name="fig..."></a>*Figure X.Y: Caption*
    # We extracted the anchor name and the visible text
    # Updated Regex to be more flexible with whitespace
    # Pattern: <a name="(.*?)"></a>\s*\*Figure (\d+\.\d+): (.*?)\*
    pattern = r'<a name="(.*?)"></a>\s*\*Figure (\d+\.\d+): (.*?)\*'
    
    matches = re.findall(pattern, md_content)
    
    if not matches:
        return ""
        
    tof = "## Table of Figures\n\n"
    for anchor, num, caption in matches:
        # Link back to the anchor
        tof += f"*   [**Figure {num}:** {caption}](#{anchor})\n"
        
    return tof

def generate_full_report_markdown(structured_results):
    # 1. Generate Front Matter (Title Page)
    # Note: Front matter includes the <page-break> at the end.
    front_matter = generate_front_matter()
    
    # 2. Start building the Main Body
    # We prefer to build this first so we can scan it for figures
    report_body = ""
    
    # Methodology & Admin Sections
    report_body += generate_methodology(structured_results)
    report_body += generate_applicability()
    report_body += generate_conformity()
    report_body += "\n---\n"
    
    # Summary Section
    report_body += "## 2. Summary of Results\n"
    report_body += "The minimum Reserve Factors (RF) for each major assembly are summarized below:\n\n"
    
    # Summary Table
    report_body += """
<table style="width: 100%; table-layout: fixed; border-collapse: collapse; font-family: sans-serif;">
<thead>
<tr style="background-color: #002D62; color: #ffffff;">
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
        
        report_body += f'<tr>'
        report_body += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle;">{chapter}</td>'
        report_body += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; word-break: break-all;">{sanitize_for_pdf(crit_comp)}</td>'
        report_body += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; text-align: center;"><b>{rf_display}</b></td>'
        report_body += f'<td style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; text-align: center; color: {status_color};"><b>{status}</b></td>'
        report_body += f'</tr>'

    report_body += "</tbody></table>\n\n---\n"

    # 3. Generate Chapters
    chapter_num = 3
    # Load Knowledge Base
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    knowledge_base = {}
    if os.path.exists(kb_path):
        import json
        with open(kb_path, 'r') as f:
            knowledge_base = json.load(f)

    for chapter_name, components in structured_results.items():
        if not components: continue
        report_body += f"## {chapter_num}. {chapter_name} Substantiation\n"
        
        # --- IMAGE INJECTION ---
        img_path = get_chapter_image(chapter_name)
        if img_path:
            report_body += f'![{chapter_name} Structure]({img_path})\n\n'
            # Add Anchor for TOF
            anchor = f"fig_{chapter_num}_1"
            report_body += f'<a name="{anchor}"></a>*Figure {chapter_num}.1: Typical {chapter_name} Structure*\n\n'
        
        # --- KNOWLEDGE INJECTION ---
        kb_info = knowledge_base.get(chapter_name)
        if kb_info:
            report_body += f"### {chapter_num}.1 Component Description\n"
            report_body += f"{kb_info.get('description', '')}\n\n"
            
            # Material Context
            material_info = kb_info.get('material')
            if material_info:
                report_body += f"**Material Specification:** {material_info}\n\n"
        
        # --- AI ASSESSMENT ---
        report_body += f"### {chapter_num}.2 Assessment summary\n"
        ai_text = f"{generate_chapter_assessment(chapter_name, components)}\n\n"
        print(ai_text)
        report_body += ai_text
        
        # --- CHART INJECTION ---
        chart_path = generate_rf_chart(chapter_name, components)
        if chart_path:
            # Convert to forward slashes for Markdown/HTML
            chart_path = chart_path.replace("\\", "/")
            report_body += f"### {chapter_num}.3 Margin Overview\n"
            report_body += "The following chart vizualizes the top 10 most critical components in this section. "
            report_body += "Bars in **Red** indicate a failure (RF < 1.0), **Orange** indicates marginal performance (1.0 < RF < 1.5), and **Green** indicates healthy margins (RF > 1.5).\n\n"
            report_body += f'![{chapter_name} RF Chart]({chart_path})\n\n'
            # Add Anchor for TOF
            anchor = f"fig_{chapter_num}_2"
            report_body += f'<a name="{anchor}"></a>*Figure {chapter_num}.2: Critical Reserve Factors - {chapter_name}*\n\n'

        # --- DATA TABLES ---
        report_body += f"### {chapter_num}.4 Tabulated Margins\n"
        report_body += "The table below provides detailed quantitative results for the critical components. "
        report_body += "It lists the governing Load Case, the Applied and Allowable loads, and the specific Failure Mode (e.g., Shear, Buckling) driving the criticality.\n\n"
        report_body += format_data_table(components, top_n=30) + "\n\n"
        chapter_num += 1
            
    # --- APPENDICES ---
    report_body += "\n---\n"
    report_body += generate_appendices()
    
    # 4. Generate TOC and TOF
    
    # FIX APPLIED HERE:
    # 1. Added style="page-break-after: avoid;" to the <h1>
    # 2. Removed the \n between the h1 and the placeholder to glue them together
    toc_section = '<h1 class="toc-header" style="page-break-after: avoid;">Table of Contents</h1>\n<div>[[TOC_PLACEHOLDER]]</div>\n[[PDF_NEXTPAGE]]\n'
    
    # Generate TOF from body
    tof_content = generate_table_of_figures(report_body)
    tof_section = ""
    if tof_content:
        tof_section = tof_content + "\n[[PDF_NEXTPAGE]]\n"
        
    # 5. Assemble Final Report
    full_report = front_matter + toc_section + tof_section + report_body
    
    return full_report
    
os.environ["GOOGLE_API_KEY"] = "AIzaSyD2iRaMSj48J3fDA-nq1b6yiR983B5u-K0"

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

def sanitize_for_pdf(text):
    """
    Injects a space after characters that typically form long unbroken strings.
    This allows the PDF engine to wrap the text naturally at these points.
    """
    if isinstance(text, str):
        # We add a space after common path/file delimiters
        for char in ["_", "\\", "/", "."]:
            text = text.replace(char, f"{char} ")
    return text

def generate_front_matter():
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    # We use Raw HTML for the tables to force specific column widths.
    # Markdown tables do not support width control.
    
    return f"""
# ENGINEERING REPORT

**Pilatus Aircraft Ltd.** Stans, Switzerland

<table style="width:100%; table-layout: fixed; border: none; margin-bottom: 20px;">
    <col width="30%">
    <col width="70%">
    <tbody>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Affected Aircraft:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;">PC-24</td>
        </tr>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Title:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Automated Stress Analysis: Flap & Support Structure</b></td>
        </tr>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Report Number:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>ER-24-AUTO-001</b></td>
        </tr>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Issue:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;">01</td>
        </tr>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Date:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;">{date_str}</td>
        </tr>
        <tr>
            <td style="border: none; padding: 4px; vertical-align: top;"><b>Issuing Office:</b></td>
            <td style="border: none; padding: 4px; vertical-align: top;">EXE</td>
        </tr>
    </tbody>
</table>

<div style="font-size: 8pt; color: #555; border-top: 1px solid #ccc; border-bottom: 1px solid #ccc; padding: 10px 0; margin: 20px 0;">
    <b>PROPRIETARY NOTICE</b><br>
    This document contains Pilatus Aircraft Limited (in this document called Pilatus) proprietary information and shall at all times remain the property of Pilatus; no intellectual property right or licence is granted by Pilatus in connection with any information contained in it. It is supplied on the express condition that said information is treated as confidential, shall not be used for any purpose other than that for which it is supplied, shall not be disclosed in whole or in part, to third parties other than the Pilatus Group members and associated Partners, their subcontractors and suppliers (to the extent of their involvement in Pilatus projects), without Pilatus prior written consent.
</div>

### APPROVAL RECORD

<table style="width: 100%; table-layout: fixed; border-collapse: collapse; word-wrap: break-word; font-family: sans-serif;">
    <thead>
        <tr style="background-color: #002D62; color: #ffffff;">
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


def generate_methodology(structured_results):
    # Load Knowledge Base
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    knowledge_base = {}
    if os.path.exists(kb_path):
        import json
        with open(kb_path, 'r') as f:
            knowledge_base = json.load(f)

    # Collect Methods
    methods = []
    for chapter in structured_results.keys():
        kb_info = knowledge_base.get(chapter)
        if kb_info and 'analysis_method' in kb_info:
            methods.append(f"*   **{chapter}:** {kb_info['analysis_method']}")
    
    method_text = "\n".join(methods) if methods else "Standard static analysis methods were applied."

    return f"""## 1. Introduction & Methodology
### 1.1 Scope
This report documents the structural substantiation of the Flap and Flap Support Structure for the PC-24 aircraft. The analysis covers static strength under critical flight loads.

### 1.2 Analysis Criteria
The structure is analyzed in accordance with **EASA CS-23** (Amendment 3).
* **Static Strength:** Compliance is shown by analysis (§23.305, §23.307).
* **Material Allowables:** A-Basis values are used for primary structure; B-Basis for redundant structure.
* **Fitting Factors:** A fitting factor of 1.15 is applied to all fittings and bearing checks (§23.625).

### 1.3 Tools & Methods
Internal loads were extracted from the Simcenter Nastran Finite Element Model (FEM). Margins of Safety (MS) and Reserve Factors (RF) were calculated using validated Pilatus Engineering Stress Sheets (PESS).

**Specific Analysis Methods:**
{method_text}
"""


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "../../config.json")
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def generate_applicability():
    config = load_config()
    items = config.get("applicability", [])
    
    rows = ""
    for item in items:
        rows += f"""<tr>
<td style="border: 1px solid #ccc; padding: 8px;">{item.get('pn', 'N/A')}</td>
<td style="border: 1px solid #ccc; padding: 8px;">{item.get('desc', 'N/A')}</td>
</tr>"""

    return f"""### 1.4 Applicability
The following aircraft assemblies are covered by this Stress Report:

<table style="width: 100%; border-collapse: collapse; font-family: sans-serif;">
<thead>
<tr style="background-color: #002D62; color: #ffffff;">
<th style="width: 30%; border: 1px solid #ccc; padding: 8px; text-align: left;">Part Number</th>
<th style="width: 70%; border: 1px solid #ccc; padding: 8px; text-align: left;">Description</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
"""

def generate_conformity():
    config = load_config()
    compliance = config.get("compliance", {})
    basis = compliance.get("basis", "EASA CS-23")
    
    paragraphs = ""
    for para in compliance.get("paragraphs", []):
         paragraphs += f"*   **{para.get('id')}** - {para.get('desc')}\n"

    return f"""### 1.5 Statement of Compliance
The structure analyzed in this report has been shown to comply with the applicable requirements of **{basis}**.

Specific compliance is demonstrated for:
{paragraphs}

All margins of safety are positive (MS > 0.00), corresponding to a Reserve Factor (RF) ≥ 1.00.
"""

def format_data_table(components_data, top_n=25):
    # Load LC Mapping
    lc_map_path = os.path.join(os.path.dirname(__file__), "load_case_mapping.json")
    lc_map = {}
    if os.path.exists(lc_map_path):
        import json
        with open(lc_map_path, 'r') as f:
            lc_map = json.load(f)

    rows = []
    
    for name, data in components_data.items():
        if not data or not isinstance(data, dict): continue
        valid_cases = {k: v for k, v in data.items() if isinstance(v, dict) and 'RF' in v}
        if not valid_cases: continue
        
        crit_lc_id = min(valid_cases, key=lambda k: valid_cases[k]['RF'])
        crit_data = valid_cases[crit_lc_id]
        
        # Get Description
        lc_desc = lc_map.get(str(crit_lc_id), f"LC {crit_lc_id}")
        
        rows.append({
            "Component ID": sanitize_for_pdf(name), 
            "Load Case": lc_desc,
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
    try: 
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
    except Exception as e:
        return f"Error generating chapter assessment: {e}"



def get_chapter_image(chapter_name):
    """
    Determines the best generic image for a chapter.
    Returns the absolute path or None.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../inputs/images"))
    
    image_map = {
        # Standard Names (from organizer)
        "Skin Panels": "skin.jpg",
        "Rib Structure": "rib.jpg",
        "Spars & Webs": "spar.jpg",
        "Fittings & Joints": "joint.jpg",
        "Stringers & Stiffeners": "spar.jpg",
        
        # Actual Names seen in Live Report (from existing logic)
        "Structural Elements (Panels & Shells)": "skin.jpg",
        "Joints & Interface Loads": "joint.jpg"
    }
    
    filename = image_map.get(chapter_name)
    print(f"DEBUG: Chapter '{chapter_name}' -> Image Filename: '{filename}'")
    
    if not filename: return None
    
    full_path = os.path.join(base_dir, filename)
    print(f"DEBUG: Full Path Resolved: '{full_path}'")
    
    if os.path.exists(full_path):
        # Return path formatted for Markdown (forward slashes are safer)
        final_path = full_path.replace("\\", "/")
        print(f"DEBUG: Path Exists! Returning: '{final_path}'")
        return final_path
    
    print(f"DEBUG: Path does NOT exist.")
    return None


def generate_appendices():
    """
    Scans the inputs/ directory and generates a table of reference documents.
    """
    inputs_dir = os.path.join(os.path.dirname(__file__), "../../inputs")
    rows = ""
    valid_exts = {'.xlsx', '.xlsm', '.dat', '.op2', '.pdf'}
    
    if os.path.exists(inputs_dir):
        for root, dirs, files in os.walk(inputs_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    file_path = os.path.join(root, file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    rel_path = os.path.relpath(file_path, inputs_dir)
                    
                    # Force breaks in the path string
                    safe_path = sanitize_for_pdf(rel_path)
                    
                    rows += f"""<tr>
<td style="border: 1px solid #ccc; padding: 8px; vertical-align: top; overflow: hidden;">
    <div style="word-wrap: break-word; word-break: break-all; width: 100%;">{safe_path}</div>
</td>
<td style="border: 1px solid #ccc; padding: 8px; vertical-align: top;">{size_mb:.2f} MB</td>
<td style="border: 1px solid #ccc; padding: 8px; vertical-align: top;">{mod_time}</td>
</tr>"""

    if not rows:
        return ""

    return f"""## Appendix A: Reference Documents
The following input files were used as the basis for this analysis:

<table style="width: 100%; table-layout: fixed; border-collapse: collapse; font-family: sans-serif;">
<thead>
<tr style="background-color: #002D62; color: #ffffff;">
<th style="width: 60%; border: 1px solid #ccc; padding: 8px; text-align: left;">File Name</th>
<th style="width: 20%; border: 1px solid #ccc; padding: 8px; text-align: left;">Size</th>
<th style="width: 20%; border: 1px solid #ccc; padding: 8px; text-align: left;">Date Modified</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
"""

