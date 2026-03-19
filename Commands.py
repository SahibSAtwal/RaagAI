import os
import sys
import pandas as pd
import RaagEngine as engine
from RaagScraper import run_scraper
import time
import zipfile
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("\n" + "="*50)
    print("                     RAAG AI")
    print("="*50)

def sync_master_raw():
    print("\nAuto-Syncing Master Raw...")
    files = [f for f in os.listdir(engine.RAW_FOLDER) if f.endswith('.csv') and "MASTER" not in f]
    if not files: return
    all_dfs = [pd.read_csv(os.path.join(engine.RAW_FOLDER, f)) for f in files]
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv(os.path.join(engine.RAW_FOLDER, "MASTER_COMBINED_RAW.csv"), index=False)
    print(f"Success: Master updated ({len(combined)} Raags total).")

def main_loop():
    while True:
        print_header()
        print(" [1] SCRAPE   - Fetch & Auto-Sync Data")
        print(" [2] PROCESS  - Run Gravity Math (Choose Dataset)")
        print(" [3] MAP      - Open 3D Interface (PlotImages)")
        print(" [4] SEARCH   - Find Raag Details & Coordinates")
        print(" [5] COMPARE  - Check similarities between 2 Raags")
        print(" [6] STATS    - Database Analytics (Note Frequency)")
        print(" [7] BACKUP   - Create Timestamped ZIP of all data")
        print(" [8] EXIT     - Close Program")
        print("-" * 50)
        
        cmd = input("Enter Command #: ").strip()

        if cmd == '1':
            run_scraper()
            sync_master_raw()
            input("\nPress Enter...")

        elif cmd == '2':
            files = [f for f in os.listdir(engine.RAW_FOLDER) if f.endswith('.csv')]
            for i, f in enumerate(files, 1): print(f" [{i}] {f}")
            try:
                choice = int(input("\nSelect # (0 for All): "))
                selected = files if choice == 0 else [files[choice-1]]
                raags = engine.load_data(selected)
                if raags:
                    processed = engine.run_gravity_processing(raags)
                    engine.save_processed_files(processed, selected)
            except: print("Invalid Selection.")
            input("\nPress Enter...")

        elif cmd == '3':
            p_files = [f for f in os.listdir(engine.PROCESSED_FOLDER) if f.endswith('.csv')]
            for i, f in enumerate(p_files, 1): print(f" [{i}] {f}")
            try:
                c = int(input("\nSelect Map: "))
                f_name = p_files[c-1]
                df = pd.read_csv(os.path.join(engine.PROCESSED_FOLDER, f_name))
                engine.create_interactive_plot(df, f_name)
            except: print("Invalid Selection.")
            input("\nPress Enter...")

        elif cmd == '4':
            query = input("Enter Raag Name to search: ").strip().lower()
            m_path = os.path.join(engine.RAW_FOLDER, "MASTER_COMBINED_RAW.csv")
            if os.path.exists(m_path):
                df = pd.read_csv(m_path)
                result = df[df['Raag Name'].str.lower().contains(query, na=False)]
                print("\nSearch Results:\n", result[['Raag Name', 'Time', 'Aaroh', 'Avroh']])
            input("\nPress Enter...")

        elif cmd == '5':
            # Similarity Checker logic
            print("\nRaag Similarity Analysis coming soon...")
            input("\nPress Enter...")

        elif cmd == '6':
            m_path = os.path.join(engine.RAW_FOLDER, "MASTER_COMBINED_RAW.csv")
            if os.path.exists(m_path):
                df = pd.read_csv(m_path)
                notes = ['S','r','R','g','G','m','M','P','d','D','n','N']
                freq = df[notes].sum().sort_values(ascending=False)
                print("\n--- Swara Usage Frequency ---")
                print(freq)
                print(f"\nTotal Raags in DB: {len(df)}")
            input("\nPress Enter...")

        elif cmd == '7':
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            b_name = f"RaagAI_Backup_{ts}.zip"
            with zipfile.ZipFile(b_name, 'w') as zipf:
                for folder in [engine.RAW_FOLDER, engine.PROCESSED_FOLDER, engine.PLOT_FOLDER]:
                    for root, dirs, files in os.walk(folder):
                        for file in files:
                            zipf.write(os.path.join(root, file))
            print(f"Backup saved as {b_name}")
            input("\nPress Enter...")

        elif cmd == '8':
            sys.exit()

        clear_screen()

if __name__ == "__main__":
    main_loop()