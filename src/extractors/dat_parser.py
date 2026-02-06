import re
import json
import os

def parse_dat_mapping(dat_path):
    """
    Parses a Simcenter Nastran .dat file to extract Group/Collector mappings.
    Looks for comments like:
    $* Mesh Collector: W_Flap_UpperSkin Panel 2 Bay 6_1.27mm
    $* Mesh: CQUAD4 2601158-2601200(27) 
    """
    if not os.path.exists(dat_path):
        print(f"❌ File not found: {dat_path}")
        return None

    mapping = {}
    current_collector = None
    
    # Regex to find the Collector Name
    # Matches: $* Mesh Collector: [Capture This Part]
    collector_pattern = re.compile(r"^\$\*\s+Mesh Collector:\s+(.+)")
    
    # Regex to find Element Ranges
    # Matches: $* Mesh: CQUAD4 [StartID]-[EndID](Count)
    # Example: $* Mesh: CQUAD4 2601158-2601200(27) 
    range_pattern = re.compile(r"^\$\*\s+Mesh:\s+\w+\s+(\d+)-(\d+)\(\d+\)")

    with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Check for New Collector Group
            col_match = collector_pattern.match(line)
            if col_match:
                current_collector = col_match.group(1).strip()
                if current_collector not in mapping:
                    mapping[current_collector] = {"ids": [], "type": "panel"}
                continue

            # Check for ID Ranges associated with that Group
            if current_collector:
                range_match = range_pattern.match(line)
                if range_match:
                    start_id = int(range_match.group(1))
                    end_id = int(range_match.group(2))
                    # Create the list of IDs (inclusive)
                    id_list = list(range(start_id, end_id + 1))
                    mapping[current_collector]["ids"].extend(id_list)

    # Filter out empty groups
    final_mapping = {k: v for k, v in mapping.items() if v["ids"]}
    
    print(f"✅ Parsed {len(final_mapping)} components from .dat file")
    return final_mapping

if __name__ == "__main__":
    # --- TEST RUN ---
    # Update this path to your actual .dat file location
    DAT_FILE = r"inputs/op2/pc24-flap_neutral_n00_normal_r1.0_s-pc24-flap_neutral_n00_normal_r.dat"
    
    result = parse_dat_mapping(DAT_FILE)
    
    if result:
        # Save to JSON to be used by the OP2 Reader
        with open("model_mapping.json", "w") as f:
            json.dump(result, f, indent=4)
        print("💾 Mapping saved to 'model_mapping.json'")
        
        # Preview
        first_key = list(result.keys())[0]
        print(f"\nExample Entry:\n'{first_key}': {result[first_key]['ids'][:5]}...")