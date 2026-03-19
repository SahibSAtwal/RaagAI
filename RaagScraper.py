import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
RAW_FOLDER = "RawRaagData"
os.makedirs(RAW_FOLDER, exist_ok=True)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Thaat Normalization Dictionary
THAAT_MAP = {
    "asawari": "Asavari", "asavari": "Asavari",
    "bhairav": "Bhairav", "bhairavi": "Bhairavi",
    "bilawal": "Bilawal", "kafi": "Kafi",
    "kalyan": "Kalyan", "khamaaj": "Khamaj", "khamaj": "Khamaj",
    "marwa": "Marwa", "poorvi": "Purvi", "purvi": "Purvi", "todi": "Todi"
}

def parse_sargam_to_bools(sargam_string):
    """Converts notation strings into 12-note boolean columns."""
    notes = ['S', 'r', 'R', 'g', 'G', 'm', 'M', 'P', 'd', 'D', 'n', 'N']
    results = {note: False for note in notes}
    if pd.isna(sargam_string) or not sargam_string: return results
    # Clean notation: remove non-alphabetic chars (keeps S, r, R, etc.)
    clean = re.sub(r"[^a-zA-Z]", "", str(sargam_string))
    for note in notes:
        if note in clean: results[note] = True
    return results

def get_all_raag_links(start_url):
    raags = []
    seen_urls = set()
    
    # 1. Raga Junglism Specific Indexing (Div/List based)
    # not working 429 error
    if "ragajunglism.org" in start_url:
        print("--- Raga Junglism: Initiating Index Scan ---")
        try:
            res = requests.get(start_url, headers=HEADERS, timeout=15)
            res.raise_for_status() # Ensure the request was successful
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # The site uses Elementor; target the widget containers
            content_containers = soup.find_all(class_=["elementor-widget-container", "elementor-text-editor"])
            
            for container in content_containers:
                # Find all links within these containers
                for a in container.find_all('a', href=True):
                    href = a['href']
                    raga_name = a.get_text(strip=True)
                    
                    # Ensure we are getting valid raga names (not empty or just symbols)
                    # and filtering for internal raga pages
                    if "/ragas/" in href and raga_name and href not in seen_urls:
                        # Exclude the masterlist itself and broad category pages
                        if href.endswith(('/masterlist/', '/ragas/', '/thaat/')):
                            continue
                            
                        seen_urls.add(href)
                        raags.append({"name": raga_name, "url": href})
                        
        except Exception as e: 
            
            print(f"Junglism Index Error: {e}")
        return raags

    # 2. Sound of India Specific Indexing (Table-based Link Extraction)
    if "soundofindia.com" in start_url:
        print("--- Sound of India: Initiating Deep Link Extraction ---")
        try:
            res = requests.get(start_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Scans for the raaga_details.asp pattern
            for a in soup.find_all('a', href=re.compile(r'raaga_details\.asp|show_raag\.asp')):
                href = a['href']
                full_url = requests.compat.urljoin("http://www.soundofindia.com/", href)
                name = a.get_text(strip=True)
                if full_url not in seen_urls and len(name) > 1:
                    seen_urls.add(full_url)
                    raags.append({"name": name, "url": full_url})
        except Exception as e: print(f"SOI Index Error: {e}")
        return raags

    # 3. Phase 1: General Global Indexing (Catch-all)
    print("--- Phase 1: Deep Scanning General Index Page ---")
    try:
        res = requests.get(start_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Pattern matching for common Hindustani music database URLs
            if any(x in href.lower() for x in ["/ragas/", "/raag-", "show_raag", "raaga_details", ".php", ".htm"]):
                full_url = requests.compat.urljoin(start_url, href)
                name = link.get_text(strip=True)
                if len(name) > 2 and full_url not in seen_urls:
                    seen_urls.add(full_url)
                    raags.append({"name": name, "url": full_url})
    except Exception as e: print(f"Index Error: {e}")
    return raags

def scrape_single_raag(r_item):
    try:
        page = requests.get(r_item['url'], headers=HEADERS, timeout=10)
        psoup = BeautifulSoup(page.text, 'html.parser')
        
        # Enhanced Name Search
        name_tag = psoup.find(class_="heading") or psoup.find('font', size="5") or psoup.find('h1') or psoup.find('b')
        actual_name = name_tag.get_text(strip=True).replace("Raaga", "").strip() if name_tag else r_item['name']
        if "not found" in actual_name.lower(): return None

        # Master Data Dictionary
        data = {"Time": "", "Aaroh": "", "Avroh": "", "Thaat": "", "Vadi": "", "Samvadi": ""}
        text_content = psoup.get_text(separator=" ")

        # --- STRATEGY H: Junglism List/Div Scraper ---
        if "ragajunglism.org" in r_item['url']:
            for li in psoup.find_all('li'):
                txt = li.get_text(strip=True).lower()
                if "parent scale" in txt or "thaat" in txt:
                    data["Thaat"] = li.get_text(strip=True).split(':')[-1].strip()
                elif "aaroh" in txt:
                    data["Aaroh"] = li.get_text(strip=True).split(':')[-1].strip()
                elif "avroh" in txt:
                    data["Avroh"] = li.get_text(strip=True).split(':')[-1].strip()

        # --- STRATEGY F: Sound of India Cell Scraper ---
        for td in psoup.find_all('td', class_='label'):
            l_txt = td.get_text(strip=True).lower().replace(':', '')
            v_td = td.find_next_sibling('td')
            if v_td:
                v_txt = v_td.get_text(strip=True)
                if "aaroha" in l_txt: data["Aaroh"] = v_txt
                elif "avaroha" in l_txt: data["Avroh"] = v_txt
                elif "thaat" in l_txt: data["Thaat"] = v_txt
                elif "prahar" in l_txt or "time" in l_txt: data["Time"] = v_txt
                elif "vaadi" in l_txt:
                    if "/" in v_txt:
                        parts = v_txt.split("/")
                        data["Vadi"] = parts.strip()
                        data["Samvadi"] = parts.strip() if len(parts) > 1 else ""
                    else: data["Vadi"] = v_txt

        # --- STRATEGY A: Standard Table (Horizontal td in tr) ---
        for tr in psoup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                k = tds.get_text(separator=" ", strip=True).lower().replace(':', '')
                v = tds.get_text(separator=" ", strip=True)
                mapping = {"aaroh": "Aaroh", "avroh": "Avroh", "time": "Time", "thaat": "Thaat", "vadi": "Vadi", "samvadi": "Samvadi"}
                for k_check, target in mapping.items():
                    if k_check in k and not data[target]:
                        data[target] = v

        # --- STRATEGY B: Sibling Search (Bold Labels / Recursive Text Recovery) ---
        for label_tag in psoup.find_all(['strong', 'b', 'font', 'span']):
            l_txt = label_tag.get_text(strip=True).lower().replace(':', '')
            if any(x in l_txt for x in ["aaroh", "avroh", "ascending", "descending", "time", "vadi"]):
                content = ""
                # Search through following text nodes or siblings
                for sibling in label_tag.next_siblings:
                    if isinstance(sibling, str) and len(sibling.strip()) > 1:
                        content = sibling.strip().strip(':').strip()
                        break
                    if hasattr(sibling, 'name') and sibling.name in ['br', 'span']:
                        continue
                if content:
                    if ("aaroh" in l_txt or "ascending" in l_txt) and not data["Aaroh"]: data["Aaroh"] = content
                    elif ("avroh" in l_txt or "descending" in l_txt) and not data["Avroh"]: data["Avroh"] = content
                    elif "time" in l_txt and not data["Time"]: data["Time"] = content
                    elif "vadi" in l_txt and not data["Vadi"]: data["Vadi"] = content

        # --- STRATEGY C: Vertical Table Row-Jumper ---
        rows = psoup.find_all('tr')
        for i, tr in enumerate(rows):
            row_txt = tr.get_text(strip=True).lower().replace(':', '')
            # If label is in its own row, look at the next row for the value
            if row_txt in ["aaroh", "avroh", "time", "thaat"] and i + 1 < len(rows):
                val = rows[i+1].get_text(strip=True)
                target = row_txt.capitalize()
                if not data.get(target): data[target] = val

        # --- STRATEGY E: Regex Global Swar Sweep ---
        if not data["Aaroh"]:
            m = re.search(r"(?:Aaroh|Ascending scale)[a-z\s:]+([SrgGmMPdnN\s,'\-]{5,})", text_content, re.I)
            if m: data["Aaroh"] = m.group(1).strip()
        if not data["Avroh"]:
            m = re.search(r"(?:Avroh|Descending scale)[a-z\s:]+([SrgGmMPdnN\s,'\-]{5,})", text_content, re.I)
            if m: data["Avroh"] = m.group(1).strip()

        # --- STRATEGY G: TECHNICAL KEYWORD SCAVENGER (Last Resort) ---
        note_check = parse_sargam_to_bools(f"{data['Aaroh']} {data['Avroh']}")
        if not any(note_check.values()):
            scavenge_map = {
                "Aaroh": [r"Aaroha?", r"Ascending"], 
                "Avroh": [r"Avaroha?", r"Descending"], 
                "Thaat": [r"Thaat", r"Parent Scale"], 
                "Time": [r"Time", r"Prahar", r"Samay"]
            }
            for key, patterns in scavenge_map.items():
                if not data[key]:
                    for p in patterns:
                        match = re.search(fr"{p}\s*[:\-]\s*([^\n\r.]+)", text_content, re.I)
                        if match:
                            data[key] = match.group(1).strip()
                            break

        # --- DATA NORMALIZATION & CLEANING ---
        raw_thaat = str(data["Thaat"]).lower().strip()
        for key, clean_val in THAAT_MAP.items():
            if key in raw_thaat:
                data["Thaat"] = clean_val
                break
        
        # Strip trailing labels left inside values
        for k in ["Aaroh", "Avroh"]:
            data[k] = re.sub(r"^(Aaroh|Avroh|Ascending|Descending|Aaroha|Avaroha)\s*:?\s*", "", str(data[k]), flags=re.I)

        entry = {"Raag Name": actual_name, "URL": r_item['url']}
        entry.update(data)
        entry.update(parse_sargam_to_bools(f"{data['Aaroh']} {data['Avroh']}"))
        return entry
    except:
        return None

def run_scraper():
    index_url = input("Enter Website Index URL: ").strip()
    if not index_url: return

    site_tag = index_url.split('//')[-1].split('.')
    raw_path = os.path.join(RAW_FOLDER, f"{site_tag}_Raw_Data.csv")

    raags_list = get_all_raag_links(index_url)
    total = len(raags_list)
    if total == 0: 
        print("No Raags found. Check the URL.")
        return

    print(f"\n--- Phase 2: Mixed Scraping {total} Raags (15 Cores max) ---")

    all_data = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(scrape_single_raag, r): r for r in raags_list}
        count = 0
        for future in as_completed(futures):
            res = future.result()
            if res:
                all_data.append(res)
                sys.stdout.write(f"\rProgress: [{count+1}/{total}] Scraped: {res['Raag Name'][:15]}...")
            count += 1
            sys.stdout.flush()

    if not all_data:
        print("\nFailed to extract data.")
        return

    df = pd.DataFrame(all_data)
    base = ["Raag Name", "URL", "Time", "Aaroh", "Avroh", "Thaat", "Vadi", "Samvadi"]
    notes = ['S', 'r', 'R', 'g', 'G', 'm', 'M', 'P', 'd', 'D', 'n', 'N']
    
    for col in base + notes:
        if col not in df.columns: df[col] = ""

    # Prevent numeric Time ranges (like 09-12) from becoming dates in Excel
    if 'Time' in df.columns:
        df['Time'] = df['Time'].apply(lambda x: f"'{x}" if isinstance(x, str) and re.match(r'^\d+-\d+$', x) else x)

    final_df = df[base + notes]
    final_df.to_csv(raw_path, index=False)
    print(f"\n\nComplete: Scraped {len(all_data)} items to: {raw_path}")

if __name__ == "__main__":
    run_scraper()