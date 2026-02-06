import os
from langchain_google_genai import ChatGoogleGenerativeAI
# UPDATED IMPORTS for Chat Model compatibility
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURATION ---
os.environ["GOOGLE_API_KEY"] = "your-key-here"

def get_llm():
    """Initializes the Gemini Model."""
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

def generate_stress_summary(component_name, analysis_data):
    """
    Generates a technical summary paragraph for a specific component.
    """
    llm = get_llm()
    
    # --- 1. Define the Persona (System Message) ---
    system_instruction = """You are a Senior Stress Engineer writing a certification report for the PC-24 aircraft.
    Write a formal "Summary of Findings" paragraph based on the analysis data provided.

    ### STYLE GUIDE (Mimic this tone):
    - "The critical pressure load cases and aileron orientations are utilized."
    - "It is shown that the front spar is able to support the ultimate loads without failure."
    - Use passive voice. Be concise. Focus on margins (RF) and critical failure modes.
    """

    # --- 2. Define the Data Input (Human Message) ---
    user_input_template = """### INPUT DATA:
    Component: {component}
    Critical Load Case: {load_case}
    Failure Mode: {mode}
    Applied Load: {applied}
    Allowable Load: {allowable}
    Reserve Factor (RF): {rf}
    Status: {status}

    ### YOUR ENGINEERING SUMMARY:
    """
    
    # --- 3. Build the Correct Prompt Object ---
    # FIX: We wrap the messages in a ChatPromptTemplate. This IS a Runnable.
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("human", user_input_template),
    ])

    # --- 4. Build the Chain ---
    chain = prompt | llm | StrOutputParser()
    
    # --- Data Prep ---
    # Find the critical load case (lowest RF)
    try:
        # Filter out error strings or incomplete data
        valid_cases = {k: v for k, v in analysis_data.items() if isinstance(v, dict) and 'RF' in v}
        
        if not valid_cases:
             return f"Analysis data for {component_name} is incomplete or contains errors."

        critical_lc = min(valid_cases, key=lambda k: valid_cases[k]['RF'])
        data = valid_cases[critical_lc]
        
        # Invoke the chain
        response = chain.invoke({
            "component": component_name,
            "load_case": critical_lc,
            "mode": data.get("Failure_Mode", "General Stability"),
            "applied": data.get("Applied_Load", "N/A"),
            "allowable": data.get("Allowable", "N/A"),
            "rf": data.get("RF", "N/A"),
            "status": "PASS" if data.get("RF", 0) > 1.0 else "FAIL"
        })
        return response
        
    except Exception as e:
        return f"Error generating summary for {component_name}: {str(e)}"

def generate_full_report_markdown(full_results_json):
    """
    Iterates through all analyzed components and builds a Markdown report.
    """
    # Handle the structure returned by the API
    results = full_results_json.get("results", full_results_json)
    
    md_report = "# Automated Stress Analysis Report\n\n"
    
    # Process Elements (Panels)
    if "Elements" in results:
        md_report += "## 1. Skin Panel Analysis\n"
        for name, data in results["Elements"].items():
            if not data: continue
            summary = generate_stress_summary(name, data)
            md_report += f"### 1.1 {name}\n{summary}\n\n"

    # Process Freebodies (Joints)
    if "Freebodies" in results:
        md_report += "## 2. Joint & Fitting Analysis\n"
        for name, data in results["Freebodies"].items():
            if not data: continue
            summary = generate_stress_summary(name, data)
            md_report += f"### 2.1 {name}\n{summary}\n\n"
            
    return md_report