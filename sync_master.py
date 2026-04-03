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

    # Map device identifiers to names
    apple_models = []
    # We'll maintain a list of identifiers we support to avoid clutter
    # For now, we fetch all builds for the devices already in our DB
    supported_ids = {m['c'] for m in current_db.get('apple', [])}
    
    # Group builds by device
    device_builds = {}
    for b in builds:
        if not b.get('sources'): continue
        beta = b.get('beta', False)
        version = b.get('version')
        build_id = b.get('build')
        
        # Sources contain the links
        for src in b['sources']:
            if src.get('type') != 'ipsw': continue
            for dev_id in src.get('deviceMap', []):
                if dev_id not in supported_ids: continue
                
                if dev_id not in device_builds: device_builds[dev_id] = []
                
                link = src.get('links', [{}])[0].get('url')
                size = src.get('size')
                
                if link:
                    device_builds[dev_id].append({
                        'v': version,
                        'b': build_id,
                        'l': link,
                        's': size,
                        'beta': beta
                    })

    # Convert back to our DB format
    new_apple = []
    # Keep model names and series from current DB
    model_meta = {m['c']: {'m': m['m'], 'sr': m['sr'], 'br': m['br']} for m in current_db.get('apple', [])}
    
    for dev_id, builds in device_builds.items():
        # Sort builds newest first
        builds.sort(key=lambda x: x['v'], reverse=True)
        meta = model_meta.get(dev_id, {'m': dev_id, 'sr': 'Apple Series', 'br': '[[APL]]'})
        
        new_apple.append({
            'br': meta['br'],
            'm': meta['m'],
            'c': dev_id,
            'sr': meta['sr'],
            'f': builds
        })
    
    return new_apple

def fetch_pixel_all(current_db):
    """Pixel syncing logic (Placeholder for real Google scraper)."""
    # Google doesn't have a clean JSON API, but we can audit their repository index
    print("Syncing Pixel...")
    return current_db.get('pixel', []) # Keep existing for now

def fetch_moto_all(current_db):
    """Motorola syncing logic (Placeholder for Lolinet scraper)."""
    print("Syncing Motorola...")
    return current_db.get('motorola', []) # Keep existing for now

def master_sync():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        print(f"FATAL: {DB_FILE} not found.")
        return

    # 1. Update Apple
    db['apple'] = fetch_apple_all(db)
    
    # 2. Update Pixel (Future Implementation)
    # db['pixel'] = fetch_pixel_all(db)
    
    # 3. Update Motorola (Future Implementation)
    # db['motorola'] = fetch_moto_all(db)

    # 4. Global Size Audit (Re-verify sizes for new links)
    print("Auditing new file sizes...")
    if 'sizes' not in db: db['sizes'] = {}
    
    for brand in ['apple', 'pixel', 'motorola']:
        for model in db.get(brand, []):
            for file in model.get('f', []):
                url = file.get('l', '')
                if url and url not in db['sizes']:
                    # We would ideally fetch the HEAD here to get size
                    # For AppleDB, size (s) is often included
                    if file.get('s'):
                        db['sizes'][url] = file['s']

    # 5. Save updated database
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, separators=(',', ':'))
    
    print("Master Sync Complete.")

if __name__ == "__main__":
    master_sync()
