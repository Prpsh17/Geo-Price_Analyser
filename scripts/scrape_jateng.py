"""
Scraper Rumah123.com — Data properti Jawa Tengah (Semarang & Solo)
Mengambil data listing rumah dan menyimpan dalam format CSV
yang kompatibel dengan dataset Jabodetabek.

Kolom output: url, price_in_rp, title, address, district, city,
              land_size_m2, building_size_m2, bedrooms, bathrooms,
              carports, floors, garages, certificate, furnishing
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os
import json

# ============================================================
# KONFIGURASI
# ============================================================
CITIES = {
    'semarang': 'Semarang',
    'surakarta': 'Solo',
}

# Berapa halaman per kota (1 halaman = ~20 listing)
# Sesuaikan jumlah sesuai kebutuhan. 50 halaman ≈ 1000 listing per kota
PAGES_PER_CITY = 5

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'jateng_house_price.csv')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# ============================================================
# FUNGSI SCRAPER
# ============================================================

def get_listing_urls(city_slug, page=1):
    """Ambil URL listing dari halaman pencarian Rumah123."""
    url = f'https://www.rumah123.com/jual/{city_slug}/rumah/'
    if page > 1:
        url += f'?page={page}'
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f'  ⚠️ Error halaman {page}: {e}')
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    urls = []
    
    # Cari link ke halaman detail properti
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if '/properti/' in href and href.startswith('/properti/'):
            full_url = 'https://www.rumah123.com' + href.split('#')[0].split('?')[0]
            if full_url not in urls:
                urls.append(full_url)
    
    return urls


def parse_price(text):
    """Parse harga dari text seperti 'Rp 1,2 Miliar' atau 'Rp 500 Juta'."""
    if not text:
        return None
    text = text.strip().lower().replace('.', '').replace(',', '.')
    
    # Cari angka
    numbers = re.findall(r'[\d.]+', text)
    if not numbers:
        return None
    
    value = float(numbers[0])
    
    if 'miliar' in text or 'm' in text:
        value *= 1_000_000_000
    elif 'juta' in text or 'jt' in text:
        value *= 1_000_000
    
    return value


def parse_number(text):
    """Parse angka dari string."""
    if not text:
        return None
    numbers = re.findall(r'[\d.]+', str(text))
    if numbers:
        try:
            return float(numbers[0])
        except:
            return None
    return None


def scrape_listing_detail(url):
    """Scrape detail dari halaman individual listing."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f'  ⚠️ Error: {e}')
        return None
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    data = {'url': url}
    
    # ---- Method 1: Cari JSON-LD structured data ----
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            json_data = json.loads(script.string)
            if isinstance(json_data, list):
                for item in json_data:
                    if item.get('@type') in ['Product', 'RealEstateListing', 'SingleFamilyResidence']:
                        json_data = item
                        break
            if isinstance(json_data, dict):
                if 'name' in json_data:
                    data['title'] = json_data['name']
                if 'offers' in json_data and isinstance(json_data['offers'], dict):
                    price = json_data['offers'].get('price')
                    if price:
                        data['price_in_rp'] = float(price)
        except:
            pass
    
    # ---- Method 2: Parse HTML meta tags ----
    og_title = soup.find('meta', property='og:title')
    if og_title and 'title' not in data:
        data['title'] = og_title.get('content', '')
    
    og_desc = soup.find('meta', property='og:description')
    if og_desc:
        data['description'] = og_desc.get('content', '')
    
    # ---- Method 3: Parse price from page text ----
    if 'price_in_rp' not in data:
        # Look for price elements
        price_el = soup.find('span', class_=re.compile(r'price|harga', re.I))
        if not price_el:
            price_el = soup.find('div', class_=re.compile(r'price|harga', re.I))
        if price_el:
            data['price_in_rp'] = parse_price(price_el.get_text())
    
    # ---- Parse property specs ----
    # Look for specification items (bedrooms, bathrooms, land size, etc.)
    text_content = soup.get_text(' ', strip=True)
    
    # Try to find specs from the page
    spec_patterns = {
        'bedrooms': [r'(\d+)\s*(?:Kamar Tidur|KT|bedroom)', r'kamar tidur\s*[:=]?\s*(\d+)'],
        'bathrooms': [r'(\d+)\s*(?:Kamar Mandi|KM|bathroom)', r'kamar mandi\s*[:=]?\s*(\d+)'],
        'land_size_m2': [r'(?:Luas Tanah|LT|land)\s*[:=]?\s*(\d+)\s*m', r'(\d+)\s*m²?\s*(?:LT|Tanah)'],
        'building_size_m2': [r'(?:Luas Bangunan|LB|building)\s*[:=]?\s*(\d+)\s*m', r'(\d+)\s*m²?\s*(?:LB|Bangunan)'],
        'carports': [r'(\d+)\s*(?:Carport|carport)', r'carport\s*[:=]?\s*(\d+)'],
        'garages': [r'(\d+)\s*(?:Garasi|garasi|garage)', r'garasi\s*[:=]?\s*(\d+)'],
        'floors': [r'(\d+)\s*(?:Lantai|lantai|floor)', r'lantai\s*[:=]?\s*(\d+)'],
    }
    
    for key, patterns in spec_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                data[key] = parse_number(match.group(1))
                break
    
    # Look for attribute sections in structured HTML
    for li in soup.find_all('li'):
        text = li.get_text(' ', strip=True).lower()
        if 'kamar tidur' in text and 'bedrooms' not in data:
            data['bedrooms'] = parse_number(text)
        elif 'kamar mandi' in text and 'bathrooms' not in data:
            data['bathrooms'] = parse_number(text)
        elif 'luas tanah' in text and 'land_size_m2' not in data:
            data['land_size_m2'] = parse_number(text)
        elif 'luas bangunan' in text and 'building_size_m2' not in data:
            data['building_size_m2'] = parse_number(text)
        elif 'carport' in text and 'carports' not in data:
            data['carports'] = parse_number(text)
        elif 'garasi' in text and 'garages' not in data:
            data['garages'] = parse_number(text)
        elif 'lantai' in text and 'floors' not in data:
            data['floors'] = parse_number(text)
        elif 'sertifikat' in text:
            data['certificate'] = text
        elif 'furnished' in text:
            if 'unfurnished' in text:
                data['furnishing'] = 'unfurnished'
            elif 'semi' in text:
                data['furnishing'] = 'semi furnished'
            else:
                data['furnishing'] = 'furnished'
    
    # Parse address from breadcrumbs or title
    breadcrumbs = soup.find_all('a', class_=re.compile(r'breadcrumb', re.I))
    if breadcrumbs:
        parts = [b.get_text(strip=True) for b in breadcrumbs]
        if len(parts) >= 2:
            data['address'] = ', '.join(parts[-2:])
    
    return data


def scrape_city(city_slug, city_name, max_pages):
    """Scrape semua listing dari satu kota."""
    all_data = []
    all_urls = []
    
    print(f'\n{"="*60}')
    print(f'🏙️  Scraping {city_name} ({city_slug}) — max {max_pages} halaman')
    print(f'{"="*60}')
    
    # Step 1: Kumpulkan URL listing
    for page in range(1, max_pages + 1):
        print(f'  📄 Mengambil halaman {page}/{max_pages}...', end=' ')
        urls = get_listing_urls(city_slug, page)
        print(f'{len(urls)} listing ditemukan')
        
        if not urls:
            print(f'  ⚠️ Tidak ada listing lagi. Berhenti.')
            break
        
        all_urls.extend(urls)
        # Delay antar halaman
        time.sleep(random.uniform(1.5, 3.0))
    
    # Deduplicate
    all_urls = list(dict.fromkeys(all_urls))
    print(f'\n  📊 Total URL unik: {len(all_urls)}')
    
    # Step 2: Scrape detail setiap listing
    for i, url in enumerate(all_urls):
        print(f'  🔍 [{i+1}/{len(all_urls)}] Scraping detail...', end=' ')
        
        detail = scrape_listing_detail(url)
        if detail and detail.get('price_in_rp'):
            detail['city'] = city_name
            # Extract district from URL
            url_parts = url.split('/')
            for part in url_parts:
                if part.startswith(city_slug + '-') or part.startswith('semarang-') or part.startswith('surakarta-'):
                    detail['district'] = part.replace(city_slug + '-', '').replace('-', ' ').title()
                    break
            
            all_data.append(detail)
            price_str = f"Rp {detail['price_in_rp']/1e9:.2f}M" if detail['price_in_rp'] >= 1e9 else f"Rp {detail['price_in_rp']/1e6:.0f}Jt"
            print(f'✅ {price_str}')
        else:
            print('❌ Skip (no price)')
        
        # Delay antar request
        time.sleep(random.uniform(2.0, 4.0))
        
        # Save progress setiap 50 listing
        if (i + 1) % 50 == 0 and all_data:
            save_progress(all_data, city_name)
    
    return all_data


def save_progress(data, city_name):
    """Simpan progress sementara."""
    temp_file = os.path.join(OUTPUT_DIR, f'_temp_{city_name.lower()}.csv')
    df = pd.DataFrame(data)
    df.to_csv(temp_file, index=False)
    print(f'  💾 Progress: {len(data)} listing disimpan ke {temp_file}')


def main():
    print('🚀 Rumah123 Scraper — Jawa Tengah')
    print('='*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_data = []
    
    for city_slug, city_name in CITIES.items():
        city_data = scrape_city(city_slug, city_name, PAGES_PER_CITY)
        all_data.extend(city_data)
        print(f'\n  ✅ {city_name}: {len(city_data)} listing berhasil di-scrape')
    
    if not all_data:
        print('\n❌ Tidak ada data berhasil di-scrape!')
        print('   Kemungkinan penyebab:')
        print('   - Website memblokir request (coba lagi nanti)')
        print('   - Struktur HTML berubah')
        return
    
    # Buat DataFrame
    columns = ['url', 'price_in_rp', 'title', 'address', 'district', 'city',
               'land_size_m2', 'building_size_m2', 'bedrooms', 'bathrooms',
               'carports', 'garages', 'floors', 'certificate', 'furnishing']
    
    df = pd.DataFrame(all_data)
    
    # Pastikan semua kolom ada
    for col in columns:
        if col not in df.columns:
            df[col] = None
    
    df = df[columns]
    
    # Simpan
    df.to_csv(OUTPUT_FILE, index=False)
    
    print(f'\n{"="*60}')
    print(f'✅ SELESAI!')
    print(f'   Total listing: {len(df)}')
    print(f'   Semarang: {len(df[df["city"]=="Semarang"])}')
    print(f'   Solo: {len(df[df["city"]=="Solo"])}')
    print(f'   File: {OUTPUT_FILE}')
    print(f'{"="*60}')
    
    # Statistik
    print(f'\n📊 Statistik Harga:')
    for city in df['city'].unique():
        city_df = df[df['city'] == city]
        prices = city_df['price_in_rp'].dropna()
        if len(prices) > 0:
            print(f'   {city}:')
            print(f'     Median: Rp {prices.median()/1e9:.2f}M')
            print(f'     Mean:   Rp {prices.mean()/1e9:.2f}M')
            print(f'     Min:    Rp {prices.min()/1e6:.0f}Jt')
            print(f'     Max:    Rp {prices.max()/1e9:.2f}M')


if __name__ == '__main__':
    main()
