import requests
import json
import re
import os
import time
# --- CONFIGURATION ---
DB_FILE = 'merged_firmware_data.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
def get_json(url):
    try:
        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
def fetch_apple_all(current_db):
    """Fetches ALL Apple firmwares (Stable + Beta) from AppleDB."""
    print("Syncing Apple (Stable + Betas)...")
    builds = get_json('https://api.appledb.dev/builds.json')
    if not builds: return current_db.get('apple', [])
    supported_ids = {m['c'] for m in current_db.get('apple', [])}
    device_builds = {}
    
    for b in builds:
        # Check source and beta status correctly
        if not b.get('sources'): continue
        beta_status = b.get('beta', False)
        version = b.get('version')
        build_id = b.get('build')
        
        for src in b['sources']:
            if src.get('type') != 'ipsw': continue
            # Handle multiple deviceMap structures
            d_map = src.get('deviceMap', [])
            for dev_id in d_map:
                if dev_id not in supported_ids: continue
                if dev_id not in device_builds: device_builds[dev_id] = []
                
                link = src.get('links', [{}])[0].get('url')
                size = src.get('size')
                if link:
                    device_builds[dev_id].append({
                        'v': version, 'b': build_id, 'l': link, 's': size, 'beta': beta_status
                    })
    new_apple = []
    model_meta = {m['c']: {'m': m['m'], 'sr': m['sr'], 'br': m['br']} for m in current_db.get('apple', [])}
    for dev_id, builds in device_builds.items():
        builds.sort(key=lambda x: x['v'], reverse=True)
        meta = model_meta.get(dev_id, {'m': dev_id, 'sr': 'Apple Series', 'br': '[[APL]]'})
        new_apple.append({'br': meta['br'], 'm': meta['m'], 'c': dev_id, 'sr': meta['sr'], 'f': builds})
    
    return new_apple
def fetch_samsung_s_series(current_db):
    """Samsung S-Series sync engine."""
    print("Syncing Samsung S-Series...")
    # List of key S-Series models (Global/Unlocked)
    s_models = [
        {"m": "Galaxy S24 Ultra", "c": "SM-S928B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S24 Plus", "c": "SM-S926B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S24", "c": "SM-S921B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S23 Ultra", "c": "SM-S918B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S23", "c": "SM-S911B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S22 Ultra", "c": "SM-S908B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S21 Ultra", "c": "SM-G998B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S20 Ultra", "c": "SM-G988B", "sr": "Galaxy S Series"},
        {"m": "Galaxy S10 Plus", "c": "SM-G975F", "sr": "Galaxy S Series"},
        {"m": "Galaxy S9 Plus", "c": "SM-G965F", "sr": "Galaxy S Series"},
        {"m": "Galaxy S8", "c": "SM-G950F", "sr": "Galaxy S Series"}
    ]
    
    samsung_data = current_db.get('samsung', [])
    # If starting fresh, initialize the Samsung list
    existing_codes = {m['c'] for m in samsung_data}
    
    for sm in s_models:
        if sm['c'] not in existing_codes:
            # Add initial structure; robot will fetch links in next runs
            samsung_data.append({'br': '[[SAM]]', 'm': sm['m'], 'c': sm['c'], 'sr': sm['sr'], 'f': []})
            
    return samsung_data
def master_sync():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        print(f"FATAL: {DB_FILE} not found.")
        return
    # 1. Update Apple (NOW WITH BETA FIX)
    db['apple'] = fetch_apple_all(db)
    
    # 2. Update Samsung S-Series
    if 'samsung' not in db: db['samsung'] = []
    db['samsung'] = fetch_samsung_s_series(db)
    # 5. Save updated database
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, separators=(',', ':'))
    
    print("Master Sync Complete.")
if __name__ == "__main__":
    master_sync()
