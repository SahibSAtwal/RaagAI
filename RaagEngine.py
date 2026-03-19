import os
import re
import numpy as np
import pandas as pd
import plotly.express as px
import webbrowser
import sys

# --- CONFIGURATION ---
RAW_FOLDER = "RawRaagData"
PROCESSED_FOLDER = "ProcessedRaagData"
PLOT_FOLDER = "PlotImages"

for folder in [RAW_FOLDER, PROCESSED_FOLDER, PLOT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

class RaagMagnitude:
    def __init__(self, data_row, source_file):
        self.source = source_file
        self.name = str(data_row.get('Raag Name', 'Unknown')).strip()
        
        # Clean data & strip Excel escape character (')
        self.raw_data = data_row.to_dict()
        if 'Time' in self.raw_data and str(self.raw_data['Time']).startswith("'"):
            self.raw_data['Time'] = str(self.raw_data['Time'])[1:]
            
        self.raw_data['Source_File'] = source_file
        
        # Swara Booleans for calculation
        self.notes = {n: bool(data_row.get(n)) for n in ['S','r','R','g','G','m','M','P','d','D','n','N']}
        self.magnitude = sum(self.notes.values())
        self.raw_data['Magnitude'] = self.magnitude
        
        # Attribute cleaning for Gravity logic
        self.vadi_samvadi = self._clean(str(data_row.get('Vadi - Samvadi', '')))
        self.vishranti = self._clean(str(data_row.get('Vishranti Sthan', '')))
        self.mukhya = self._clean(str(data_row.get('Mukhya Ang', '')))
        self.aroh_avroh = self._clean(str(data_row.get('Aaroh - Avroh', '')))
        
        # Coordinates Calculation (Initial State)
        x = 1 if self.notes['M'] else 0 
        y = sum([self.notes[k] for k in ['S', 'R', 'G', 'm', 'P', 'D', 'N']])
        z = sum([self.notes[k] for k in ['r', 'g', 'd', 'n']])
        self.current_coords = np.array([x, y, z], dtype=float)

    def _clean(self, text):
        if pd.isna(text) or text.lower() == 'nan': return ""
        return re.sub(r"[()',;/-]", "", str(text)).replace(" ", "").lower()

# --- DATA LOADING & SELECTION ---

def select_dataset():
    """Menu for standalone engine use."""
    files = [f for f in os.listdir(RAW_FOLDER) if f.endswith('.csv')]
    if not files:
        print("No CSV files found in RawRaagData!")
        return None
    
    print("\n--- Available Datasets ---")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f}")
    
    try:
        choice = int(input("\nSelect a dataset number (or 0 for ALL): "))
        return files if choice == 0 else [files[choice - 1]]
    except (ValueError, IndexError):
        return None

def load_data(selected_files):
    """Core loader used by Engine, Commands.py, and Dashboard."""
    all_raags = []
    for f in selected_files:
        path = os.path.join(RAW_FOLDER, f)
        if not os.path.exists(path): continue
        df = pd.read_csv(path)
        print(f"Loading {len(df)} raags from {f}...")
        for _, row in df.iterrows():
            all_raags.append(RaagMagnitude(row, f))
    return all_raags

# --- COMPATIBILITY BRIDGES FOR COMMANDS.PY ---

def load_all_raw_data():
    """Bridge for Command [3]: Loads combined master if it exists, else all raw files."""
    master_path = os.path.join(RAW_FOLDER, "MASTER_COMBINED_RAW.csv")
    if os.path.exists(master_path):
        return load_data(["MASTER_COMBINED_RAW.csv"])
    
    all_files = [f for f in os.listdir(RAW_FOLDER) if f.endswith('.csv')]
    return load_data(all_files)

def save_master_files(raags):
    """Bridge for Command [3]: Forces output to the Master Calculated filename."""
    return save_processed_files(raags, ["MASTER_COMBINED_RAW.csv"])

# --- THE MATH & PROCESSING ---

def run_gravity_processing(raags, weights=None):
    """Full i9 Optimized Gravity Logic with Normalization Fix."""
    if weights is None:
        weights = {'mukhya': 0.4, 'aroh_avroh': 0.3, 'vadi_samvadi': 0.2, 'vishranti': 0.1}
    
    # NORMALIZATION: Ensure weights sum to 1.0
    total_w = sum(weights.values())
    if total_w != 1.0 and total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    total = len(raags)
    for i, r1 in enumerate(raags):
        adjustment = np.array([0.0, 0.0, 0.0])
        for j, r2 in enumerate(raags):
            if i == j: continue
            for attr, weight in weights.items():
                v1, v2 = getattr(r1, attr), getattr(r2, attr)
                if v1 == v2 and v1 != "":
                    # Attraction logic: pull similar raags closer in 3D space
                    adjustment += (r2.current_coords - r1.current_coords) * weight
        
        r1.current_coords += adjustment * 0.05
        sys.stdout.write(f"\rMapping Progress: [{i+1}/{total}] Processing {r1.name}...")
        sys.stdout.flush()
    print("\nGravity processing complete.")
    return raags

def save_processed_files(raags, selected_files):
    """Ensures individual source files get their own CALCULATED_ counterparts."""
    processed_data = []
    for r in raags:
        d = r.raw_data.copy()
        d['Final_X'] = np.round(r.current_coords[0], 4)
        d['Final_Y'] = np.round(r.current_coords[1], 4)
        d['Final_Z'] = np.round(r.current_coords[2], 4)
        processed_data.append(d)
    
    df = pd.DataFrame(processed_data)
    
    for f in selected_files:
        if f == "MASTER_COMBINED_RAW.csv":
            source_df = df
            out_name = "MASTER_COMBINED_CALCULATED.csv"
        else:
            source_df = df[df['Source_File'] == f]
            out_name = f"CALCULATED_{f}"
             
        out_path = os.path.join(PROCESSED_FOLDER, out_name)
        source_df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")
    
    return df

# --- INTERFACE ---

def create_interactive_plot(df, original_filename="Master_Map"):
    """Generates 3D map in PlotImages folder with a unique name."""
    clean_name = original_filename.replace(".csv", "").replace("CALCULATED_", "")
    unique_map_path = os.path.join(PLOT_FOLDER, f"MAP_{clean_name}.html")
    
    hidden = ['Final_X', 'Final_Y', 'Final_Z', 'S','r','R','g','G','m','M','P','d','D','n','N', 
              'current_coords', 'base_coords', 'Magnitude', 'Source_File']
    
    hover_config = {col: (col not in hidden) for col in df.columns}

    fig = px.scatter_3d(
        df, x='Final_X', y='Final_Y', z='Final_Z',
        color='Magnitude', color_continuous_scale='Magma',
        hover_data=hover_config, text='Raag Name',
        title=f"Raag AI Engine: {clean_name}"
    )

    fig.update_layout(
        template="plotly_dark",
        scene=dict(
            xaxis=dict(title='Tivar (Sharpness)', range=[-0.5, 2.5]),
            yaxis=dict(title='Shudh (Naturalness)', range=[0, 8]),
            zaxis=dict(title='Komal (Flatness)', range=[0, 6])
        )
    )
    fig.write_html(unique_map_path)
    webbrowser.open('file://' + os.path.realpath(unique_map_path))
    print(f"Interactive map saved to: {unique_map_path}")

if __name__ == "__main__":
    files = select_dataset()
    if files:
        data = load_data(files)
        processed = run_gravity_processing(data)
        final_df = save_processed_files(processed, files)
        create_interactive_plot(final_df, files[0])