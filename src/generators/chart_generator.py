import matplotlib.pyplot as plt
import io
import os

def generate_rf_chart(chapter_name, components_data):
    """
    Generates a simple Bar Chart for Reserve Factors (RF).
    Saves it to a temporary file and returns the path.
    """
    try:
        # 1. Extract Data
        labels = []
        rfs = []
        colors = []
        
        for name, data in components_data.items():
            valid_rfs = [v['RF'] for k,v in data.items() if isinstance(v, dict) and 'RF' in v]
            if not valid_rfs: continue
            
            min_rf = min(valid_rfs)
            
            # Shorten label for chart
            short_name = name[:15] + "..." if len(name) > 15 else name
            
            labels.append(short_name)
            rfs.append(min_rf)
            
            # Color Logic: Red for failure, Green for pass
            if min_rf < 1.0:
                colors.append('red')
            elif min_rf < 1.5:
                colors.append('orange')
            else:
                colors.append('green')
        
        if not rfs: return None

        # Take only top 10 critical (lowest RF) to keep chart clean
        combined = sorted(zip(rfs, labels, colors), key=lambda x: x[0])[:10]
        rfs, labels, colors = zip(*combined)

        # 2. Create Plot
        plt.figure(figsize=(10, 4))
        bars = plt.barh(labels, rfs, color=colors)
        
        plt.axvline(x=1.0, color='red', linestyle='--', label='Failure Limit (RF=1.0)')
        plt.title(f'Critical Reserve Factors - {chapter_name}')
        plt.xlabel('Reserve Factor (RF)')
        plt.tight_layout()

        # 3. Save to File
        # We need a unique filename to avoid overwrites during concurrent reports
        # For simplicity in this POC, we use a fixed pattern in outputs/images
        output_dir = "outputs/images"
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = "".join([c for c in chapter_name if c.isalnum()])
        filename = f"chart_{safe_name}.png"
        full_path = os.path.abspath(os.path.join(output_dir, filename))
        
        plt.savefig(full_path)
        plt.close()
        
        return full_path

    except Exception as e:
        print(f"Chart Generation Error: {e}")
        return None
