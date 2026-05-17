"""
Script Cleaning Data Rumah Jawa Tengah
======================================
Membersihkan data mentah dari browser scraping (Instant Data Scraper / Web Scraper)
dan menghasilkan CSV bersih yang kompatibel dengan dataset Jabodetabek.

Input : data/raw/Data rumah jateng.csv
Output: data/processed/jateng_house_price_clean.csv
"""

import pandas as pd
import re
import os
import sys

# ============================================================
# KONFIGURASI PATH
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'Data rumah jateng.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'processed')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'jateng_house_price_clean.csv')


# ============================================================
# FUNGSI UTILITAS
# ============================================================

def parse_price(text):
    """
    Parse harga dari text mentah Rumah123.
    Contoh input:
      - 'Rp 473 Juta'       -> 473_000_000
      - 'Rp 2 Miliar'       -> 2_000_000_000
      - 'Rp 1,4 Miliar'     -> 1_400_000_000
      - 'Rp 2,5 Miliar Total' -> 2_500_000_000
      - 'Rp 55 Juta /m²'    -> None (harga per m², skip)
      - 'Rp 280 Ribuan /m²' -> None
    """
    if not isinstance(text, str) or not text.strip():
        return None

    text = text.strip()

    # Skip harga per m² (tidak bisa digunakan tanpa luas)
    if '/m²' in text or '/m2' in text:
        return None

    # Skip harga satuan "Ribuan"
    if 'Ribuan' in text:
        return None

    # Bersihkan suffix "Total"
    text_clean = text.replace('Total', '').strip()

    # Ganti koma Indonesia ke titik desimal
    text_clean = text_clean.replace('.', '').replace(',', '.')

    # Cari angka
    numbers = re.findall(r'[\d.]+', text_clean)
    if not numbers:
        return None

    try:
        value = float(numbers[0])
    except ValueError:
        return None

    text_lower = text_clean.lower()
    if 'miliar' in text_lower:
        value *= 1_000_000_000
    elif 'juta' in text_lower:
        value *= 1_000_000
    else:
        # Tidak ada unit, kemungkinan sudah dalam Rupiah penuh
        # Tapi biasanya Rumah123 selalu pakai Juta/Miliar
        return None

    return value


def parse_size(text):
    """
    Parse luas dari text seperti '72 m²', '288 m²'.
    Return float atau None.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    numbers = re.findall(r'[\d.]+', text.replace(',', '.'))
    if not numbers:
        return None

    try:
        val = float(numbers[0])
        return val if val > 0 else None
    except ValueError:
        return None


def parse_rooms(text):
    """
    Parse jumlah kamar dari text seperti '2', '3 + 1', '2 + 1'.
    Mengembalikan total (utama + tambahan).
    Jika teks berisi '[object Object]' atau kosong, return None.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    if 'object' in text.lower():
        return None

    # Handle format "X + Y"
    parts = text.split('+')
    total = 0
    for part in parts:
        nums = re.findall(r'\d+', part.strip())
        if nums:
            total += int(nums[0])

    return float(total) if total > 0 else None


def detect_property_type(title, url):
    """
    Deteksi tipe properti dari judul atau URL listing.
    Return: 'rumah', 'ruko', 'tanah', 'apartemen', 'kost', 'gudang', 'hotel', 'ruang_usaha', 'lainnya'
    """
    title_lower = str(title).lower() if pd.notna(title) else ''
    url_lower = str(url).lower() if pd.notna(url) else ''

    # Default
    prop_type = 'lainnya'

    # Check URL pattern: Rumah123 URL ID suffix indicates type
    # e.g., hos41449614 = house, shs9895897 = shophouse, las9114075 = land
    #        aps7607177 = apartment, kss246506 = kost, css9895813 = commercial
    #        was9896323 = warehouse, hts225656 = hotel
    url_id_match = re.search(r'-(hos|shs|las|aps|kss|css|was|hts)\d+', url_lower)
    if url_id_match:
        url_type = url_id_match.group(1)
        type_map = {
            'hos': 'rumah',
            'shs': 'ruko',
            'las': 'tanah',
            'aps': 'apartemen',
            'kss': 'kost',
            'css': 'ruang_usaha',
            'was': 'gudang',
            'hts': 'hotel',
        }
        prop_type = type_map.get(url_type, 'lainnya')

    # Override berdasarkan judul jika lebih spesifik
    if any(kw in title_lower for kw in ['ruko ', 'ruko,', 'ruko.']):
        prop_type = 'ruko'
    elif any(kw in title_lower for kw in ['tanah ', 'kavling ', 'kav ']):
        prop_type = 'tanah'
    elif any(kw in title_lower for kw in ['apartemen', 'apartment', 'studio ']):
        prop_type = 'apartemen'
    elif any(kw in title_lower for kw in ['kost', 'kos-kos', 'guesthouse']):
        prop_type = 'kost'
    elif any(kw in title_lower for kw in ['gudang']):
        prop_type = 'gudang'
    elif any(kw in title_lower for kw in ['hotel']):
        prop_type = 'hotel'
    elif any(kw in title_lower for kw in ['ruang usaha']):
        prop_type = 'ruang_usaha'

    return prop_type


def extract_location(text):
    """
    Parse lokasi dari format 'Distrik, Kota'.
    Contoh: 'Semarang Barat, Semarang' -> ('Semarang Barat', 'Semarang')
            'Laweyan, Surakarta'       -> ('Laweyan', 'Surakarta')
    """
    if not isinstance(text, str) or not text.strip():
        return None, None

    parts = [p.strip() for p in text.split(',')]
    if len(parts) >= 2:
        district = parts[0]
        city = parts[1]
        return district, city
    elif len(parts) == 1:
        return parts[0], None

    return None, None


# ============================================================
# MAIN CLEANING PIPELINE
# ============================================================

def main():
    print('=' * 60)
    print('🧹 CLEANING DATA RUMAH JAWA TENGAH')
    print('=' * 60)

    # --- 1. LOAD DATA ---
    print(f'\n📂 Loading: {INPUT_FILE}')
    if not os.path.exists(INPUT_FILE):
        print(f'❌ File tidak ditemukan: {INPUT_FILE}')
        sys.exit(1)

    df_raw = pd.read_csv(INPUT_FILE, encoding='utf-8')
    print(f'   Baris mentah: {len(df_raw)}')
    print(f'   Kolom: {len(df_raw.columns)}')

    # --- 2. MAP KOLOM ---
    # Kolom CSS class dari scraper -> nama bermakna
    # Berdasarkan analisis posisi kolom:
    cols = df_raw.columns.tolist()
    print(f'\n📋 Header asli (pertama 10): {cols[:10]}')

    # Temukan kolom berdasarkan nama persis
    col_map = {
        'harga_raw': 'Harga',
        'url': 'w-full href',
        'title': 'w-full',
        'lokasi': 'text-left',
        'deskripsi': 'text-greyText',
    }
    
    df = pd.DataFrame()
    for new_col, raw_col in col_map.items():
        if raw_col in df_raw.columns:
            df[new_col] = df_raw[raw_col]
        else:
            df[new_col] = None

    # Ekstrak semua kolom 'flex' (berisi spek: kamar, luas)
    flex_cols = [c for c in df_raw.columns if str(c).startswith('flex')]
    
    bedrooms_list, bathrooms_list, carports_list = [], [], []
    land_list, build_list = [], []

    for idx, row in df_raw.iterrows():
        rooms = []
        areas = []
        
        for fc in flex_cols:
            val = str(row[fc]).strip()
            if val and val != 'nan' and 'object' not in val:
                if 'm²' in val or 'm2' in val:
                    areas.append(val)
                else:
                    rooms.append(val)
                    
        # Assign rooms (KT, KM, Carport)
        bedrooms_list.append(rooms[0] if len(rooms) > 0 else None)
        bathrooms_list.append(rooms[1] if len(rooms) > 1 else None)
        carports_list.append(rooms[2] if len(rooms) > 2 else None)
        
        # Assign areas (LT, LB)
        land_list.append(areas[0] if len(areas) > 0 else None)
        build_list.append(areas[1] if len(areas) > 1 else None)

    df['bedrooms_raw'] = bedrooms_list
    df['bathrooms_raw'] = bathrooms_list
    df['carports_raw'] = carports_list
    df['land_size_raw'] = land_list
    df['building_size_raw'] = build_list

    print(f'\n✅ Kolom di-map dinamis: {list(df.columns)}')
    print(f'   Contoh harga: {df["harga_raw"].iloc[:3].tolist()}')
    print(f'   Contoh lokasi: {df["lokasi"].iloc[:3].tolist()}')

    # --- 3. PARSE HARGA ---
    print('\n💰 Parsing harga...')
    df['price_in_rp'] = df['harga_raw'].apply(parse_price)
    valid_prices = df['price_in_rp'].notna().sum()
    print(f'   Harga valid: {valid_prices}/{len(df)}')
    print(f'   Harga invalid (skip):')
    invalid_prices = df[df['price_in_rp'].isna()]['harga_raw'].unique()
    for p in invalid_prices[:10]:
        print(f'     - "{p}"')

    # --- 4. PARSE LOKASI ---
    print('\n📍 Parsing lokasi...')
    location_parsed = df['lokasi'].apply(lambda x: extract_location(x))
    df['district'] = location_parsed.apply(lambda x: x[0])
    df['city'] = location_parsed.apply(lambda x: x[1])

    print(f'   Kota ditemukan: {df["city"].dropna().unique().tolist()}')
    print(f'   District contoh: {df["district"].dropna().unique()[:10].tolist()}')

    # --- 5. DETEKSI TIPE PROPERTI ---
    print('\n🏠 Deteksi tipe properti...')
    df['property_type'] = df.apply(
        lambda row: detect_property_type(row.get('title', ''), row.get('url', '')),
        axis=1
    )
    type_counts = df['property_type'].value_counts()
    print(f'   Distribusi:')
    for ptype, count in type_counts.items():
        print(f'     {ptype}: {count}')

    # --- 6. PARSE UKURAN & KAMAR ---
    print('\n📐 Parsing ukuran & kamar...')
    df['land_size_m2'] = df['land_size_raw'].apply(parse_size)
    df['building_size_m2'] = df['building_size_raw'].apply(parse_size)
    df['bedrooms'] = df['bedrooms_raw'].apply(parse_rooms)
    df['bathrooms'] = df['bathrooms_raw'].apply(parse_rooms)
    df['carports'] = df['carports_raw'].apply(parse_rooms)

    print(f'   Land size valid: {df["land_size_m2"].notna().sum()}')
    print(f'   Building size valid: {df["building_size_m2"].notna().sum()}')
    print(f'   Bedrooms valid: {df["bedrooms"].notna().sum()}')

    # --- 7. FILTER: HANYA RUMAH ---
    print('\n🔍 Filter hanya tipe "rumah"...')
    df_before = len(df)
    df = df[df['property_type'] == 'rumah'].copy()
    print(f'   {df_before} -> {len(df)} (buang {df_before - len(df)} non-rumah)')

    # --- 8. FILTER: HARGA VALID ---
    print('\n🔍 Filter harga valid...')
    df_before = len(df)
    df = df[df['price_in_rp'].notna()].copy()
    print(f'   {df_before} -> {len(df)} (buang {df_before - len(df)} tanpa harga)')

    # --- 9. FILTER OUTLIER ---
    print('\n🔍 Filter outlier...')
    df_before = len(df)

    # Harga: min 50jt, max 50M
    df = df[(df['price_in_rp'] >= 50_000_000) & (df['price_in_rp'] <= 50_000_000_000)].copy()

    # Luas tanah: max 2000 m² (buang kavling industri)
    mask_lt = df['land_size_m2'].isna() | (df['land_size_m2'] <= 2000)
    df = df[mask_lt].copy()

    # Luas bangunan: max 2000 m²
    mask_lb = df['building_size_m2'].isna() | (df['building_size_m2'] <= 2000)
    df = df[mask_lb].copy()

    # Kamar tidur: max 10
    mask_kt = df['bedrooms'].isna() | (df['bedrooms'] <= 10)
    df = df[mask_kt].copy()

    print(f'   {df_before} -> {len(df)} (buang {df_before - len(df)} outlier)')

    # --- 10. ALAMAT (gabung district + city) ---
    df['address'] = df.apply(
        lambda row: f"{row['district']}, {row['city']}"
        if pd.notna(row['district']) and pd.notna(row['city'])
        else (row['district'] or row['city'] or ''),
        axis=1
    )

    # --- 11. SUSUN KOLOM FINAL ---
    # Kompatibel dengan dataset Jabodetabek
    final_columns = [
        'url', 'price_in_rp', 'title', 'address', 'district', 'city',
        'property_type', 'land_size_m2', 'building_size_m2',
        'bedrooms', 'bathrooms', 'carports'
    ]

    df_final = df[final_columns].copy()

    # --- 12. SIMPAN ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')

    # --- 13. RINGKASAN ---
    print(f'\n{"=" * 60}')
    print(f'✅ CLEANING SELESAI!')
    print(f'{"=" * 60}')
    print(f'   File output : {OUTPUT_FILE}')
    print(f'   Total listing: {len(df_final)}')
    print(f'\n📊 Per Kota:')
    for city in sorted(df_final['city'].dropna().unique()):
        city_df = df_final[df_final['city'] == city]
        print(f'   {city}: {len(city_df)} listing')

    print(f'\n📊 Statistik Harga:')
    for city in sorted(df_final['city'].dropna().unique()):
        prices = df_final[df_final['city'] == city]['price_in_rp'].dropna()
        if len(prices) > 0:
            print(f'   {city}:')
            print(f'     Count : {len(prices)}')
            print(f'     Median: Rp {prices.median()/1e9:.2f}M')
            print(f'     Mean  : Rp {prices.mean()/1e9:.2f}M')
            print(f'     Min   : Rp {prices.min()/1e6:.0f}Jt')
            print(f'     Max   : Rp {prices.max()/1e9:.2f}M')

    print(f'\n📊 Missing Values:')
    for col in final_columns:
        missing = df_final[col].isna().sum()
        pct = missing / len(df_final) * 100 if len(df_final) > 0 else 0
        print(f'   {col:20s}: {missing:3d} ({pct:.1f}%)')

    print(f'\n📊 Sample Data (5 baris pertama):')
    print(df_final.head().to_string(index=False))

    return df_final


if __name__ == '__main__':
    main()
