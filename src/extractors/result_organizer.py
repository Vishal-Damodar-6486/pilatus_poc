import re

def organize_results_into_chapters(raw_results):
    """
    Analyzes the raw Phase 2 output (which might be flat or nested)
    and organizes it into logical 'Chapters' for the report.
    """
    structured_report = {}

    # --- SCENARIO A: Already Nested (From API Phase 1) ---
    # If the extraction phase already did the job, trust it.
    if "Elements" in raw_results or "Freebodies" in raw_results:
        # We rename them to nicer "Chapter Titles"
        if "Elements" in raw_results:
            structured_report["Structural Elements (Panels & Shells)"] = raw_results["Elements"]
        if "Freebodies" in raw_results:
            structured_report["Joints & Interface Loads"] = raw_results["Freebodies"]
        return structured_report

    # --- SCENARIO B: Flat List (From Excel or Manual Upload) ---
    # We need to discover the structure dynamically.
    
    print("   -> Detecting report structure from component names...")
    
    for comp_name, data in raw_results.items():
        if not data: continue # Skip empty results
        
        # --- LOGIC: Group by Name Pattern ---
        chapter_name = "Miscellaneous Components" # Default
        
        name_lower = comp_name.lower()
        
        if "skin" in name_lower or "panel" in name_lower:
            chapter_name = "Skin Panels"
        elif "rib" in name_lower:
            chapter_name = "Rib Structure"
        elif "spar" in name_lower or "web" in name_lower:
            chapter_name = "Spars & Webs"
        elif "clip" in name_lower or "splice" in name_lower or "joint" in name_lower:
            chapter_name = "Fittings & Joints"
        elif "stringer" in name_lower or "stiffener" in name_lower:
            chapter_name = "Stringers & Stiffeners"
            
        # Initialize chapter if new
        if chapter_name not in structured_report:
            structured_report[chapter_name] = {}
            
        # Add component to chapter
        structured_report[chapter_name][comp_name] = data

    # Sort chapters alphabetically for consistency
    return dict(sorted(structured_report.items()))