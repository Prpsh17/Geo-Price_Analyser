"""
=============================================================================
Geo-Price Analyzer — Streamlit Dashboard
=============================================================================
Dashboard interaktif untuk prediksi harga properti dengan komparasi
regional Jabodetabek & Jawa Tengah.

Jalankan dengan:
    streamlit run app.py
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

# ============================================================================
# Regional Factors
# ============================================================================
# Faktor ini sekarang dihitung secara dinamis di dalam fungsi main() 
# menggunakan data yang diprediksi oleh model, sama seperti di Notebook 04.

def format_rupiah(value, _=None):
    if value >= 1e9: return f'Rp {value/1e9:.1f}M'
    elif value >= 1e6: return f'Rp {value/1e6:.0f}Jt'
    else: return f'Rp {value:,.0f}'

def adjust_price_regional(harga_jabodetabek, kota_tujuan, regional_factors):
    faktor = regional_factors.get(kota_tujuan, 0.34)
    harga_adj = harga_jabodetabek * faktor
    return {
        "kota": kota_tujuan,
        "faktor_regional": faktor,
        "harga_jabodetabek": harga_jabodetabek,
        "harga_adjusted": harga_adj,
        "selisih": harga_jabodetabek - harga_adj,
        "persen_selisih": (1 - faktor) * 100,
    }

def compare_all_regions(harga_jabodetabek, regional_factors):
    rows = []
    for kota, faktor in regional_factors.items():
        h = harga_jabodetabek * faktor
        rows.append({
            "Kota/Region": kota,
            "Faktor": faktor,
            "Estimasi Harga": h,
            "Estimasi (Format)": format_rupiah(h),
            "Selisih dari Jabodetabek": f"-{(1-faktor)*100:.0f}%" if faktor < 1 else "Basis",
        })
    return pd.DataFrame(rows)

# ============================================================================
# Page Config
# ============================================================================
st.set_page_config(
    page_title="Geo-Price Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Custom CSS
# ============================================================================
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .hero-title {
        font-size: 2.8rem; font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0;
    }
    .hero-subtitle { font-size: 1.1rem; color: #a0aec0; text-align: center; margin-top: 0; }
    .price-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px; padding: 24px;
        border: 1px solid rgba(102, 126, 234, 0.3); text-align: center; margin: 8px 0;
    }
    .price-card h3 { color: #a0aec0; font-size: 0.9rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    .price-jkt { color: #667eea; font-size: 2rem; font-weight: 800; margin: 0; }
    .price-jateng { color: #48bb78; font-size: 2rem; font-weight: 800; margin: 0; }
    .price-saving { color: #f56565; font-size: 1.4rem; font-weight: 700; margin: 0; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%); }
    .footer { text-align: center; color: #4a5568; padding: 20px; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Helper Functions
# ============================================================================

@st.cache_resource
def load_trained_model(model_path: str):
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

@st.cache_data
def load_dataset(data_path: str):
    if os.path.exists(data_path):
        return pd.read_csv(data_path)
    return None

@st.cache_data
def get_dynamic_regional_factors(_model, _le, feature_cols, project_root):
    jateng_path = os.path.join(project_root, "data", "processed", "jateng_house_price_clean.csv")
    
    # Fallback to default if no data available
    default_factors = {"Jabodetabek": 1.00, "Semarang": 0.40, "Solo": 0.38, "Yogyakarta": 0.45}
    
    if not os.path.exists(jateng_path):
        return default_factors
        
    df_jateng = pd.read_csv(jateng_path)
    df_jateng = df_jateng.dropna(subset=['land_size_m2', 'building_size_m2', 'bedrooms', 'bathrooms']).copy()
    if len(df_jateng) == 0:
        return default_factors
        
    df_jateng['carports'] = df_jateng['carports'].fillna(0)
    
    baseline_city = 'Bekasi'
    baseline_code = _le.transform([baseline_city])[0] if baseline_city in _le.classes_ else 0
    
    df_sim = df_jateng.copy()
    df_sim['city_encoded'] = baseline_code
    df_sim['garages'] = 0
    df_sim['floors'] = np.where(df_sim['building_size_m2'] > df_sim['land_size_m2'], 2, 1)
    df_sim['rasio_tanah_bangunan'] = df_sim['land_size_m2'] / df_sim['building_size_m2']
    df_sim['total_ruangan'] = df_sim['bedrooms'] + df_sim['bathrooms']
    
    try:
        df_jateng['jabodetabek_pred'] = _model.predict(df_sim[feature_cols])
        df_jateng['factor'] = df_jateng['price_in_rp'] / df_jateng['jabodetabek_pred']
        valid_factors = df_jateng[(df_jateng['factor'] >= 0.1) & (df_jateng['factor'] <= 2.0)]
        factor_per_city = valid_factors.groupby('city')['factor'].agg(['median', 'count'])
        factor_per_city = factor_per_city[factor_per_city['count'] >= 3] # Minimal 3 data
        
        factors = {"Jabodetabek": 1.00}
        for city, row in factor_per_city.iterrows():
            factors[city] = round(row['median'], 2)
            
        if len(factors) == 1: # Only Jabodetabek
            return default_factors
            
        return factors
    except Exception as e:
        print(f"Error calculating factors: {e}")
        return default_factors


# ============================================================================
# Main App
# ============================================================================

def main():
    st.markdown('<h1 class="hero-title">🏠 Geo-Price Analyzer</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-subtitle">Prediksi Harga Properti Berbasis Machine Learning — '
        'Jabodetabek & Jawa Tengah</p>', unsafe_allow_html=True
    )
    st.markdown("---")

    project_root = os.path.dirname(os.path.abspath(__file__))

    # Load models
    model_paths = {
        "Random Forest": os.path.join(project_root, "models", "random_forest_model.pkl"),
        "XGBoost": os.path.join(project_root, "models", "xgboost_model.pkl"),
        "Linear Regression": os.path.join(project_root, "models", "linear_regression_model.pkl"),
    }

    data_path = os.path.join(project_root, "data", "processed", "jabodetabek_processed.csv")

    available_models = {}
    for name, path in model_paths.items():
        m = load_trained_model(path)
        if m is not None:
            available_models[name] = m

    # Load label encoder & feature cols
    le_path = os.path.join(project_root, "models", "label_encoder.pkl")
    fc_path = os.path.join(project_root, "models", "feature_cols.pkl")
    le = load_trained_model(le_path)
    feature_cols = load_trained_model(fc_path)

    df_processed = load_dataset(data_path)

    if not available_models:
        st.error(
            "⚠️ Model belum ditraining! Jalankan notebook `03_Modeling_Evaluation.ipynb` terlebih dahulu."
        )
        st.stop()

    st.markdown("### 🎛️ Pengaturan Parameter Properti")
    col_p1, col_p2, col_p3 = st.columns(3)

    if le is not None:
        lokasi_options = sorted(le.classes_.tolist())
    else:
        lokasi_options = ["Bekasi", "Bogor", "Depok", "Jakarta Selatan", "Tangerang"]

    with col_p1:
        lokasi = st.selectbox("📍 Kota Jabodetabek (Basis)", lokasi_options)
        luas_tanah = st.number_input("📐 Luas Tanah (m²)", 36, 800, 120, step=5)
        luas_bangunan = st.number_input("🏗️ Luas Bangunan (m²)", 21, 600, 80, step=5)

    with col_p2:
        kamar_tidur = st.number_input("🛏️ Kamar Tidur", 1, 8, 3)
        kamar_mandi = st.number_input("🚿 Kamar Mandi", 1, 6, 2)
        floors = st.number_input("🏢 Jumlah Lantai", 1, 4, 2)

    with col_p3:
        carports = st.number_input("🅿️ Carport", 0, 5, 1)
        garasi = st.number_input("🚗 Garasi", 0, 5, 1)
        selected_model = st.selectbox("🤖 Pilih Model Machine Learning", list(available_models.keys()))

    # Predict
    model = available_models[selected_model]

    if le is not None and lokasi in le.classes_:
        city_code = le.transform([lokasi])[0]
    else:
        city_code = 0

    # Calculate regional factors dynamically
    regional_factors = get_dynamic_regional_factors(model, le, feature_cols, project_root)

    with col_p1:
        kota_jateng = st.selectbox(
            "🌍 Kota Jawa Tengah (Komparasi)",
            [k for k in regional_factors.keys() if k != "Jabodetabek"]
        )
    st.markdown("---")

    rasio = luas_tanah / max(luas_bangunan, 1)
    total_ruangan = kamar_tidur + kamar_mandi

    features = {
        "land_size_m2": luas_tanah,
        "building_size_m2": luas_bangunan,
        "bedrooms": kamar_tidur,
        "bathrooms": kamar_mandi,
        "carports": carports,
        "garages": garasi,
        "floors": floors,
        "city_encoded": city_code,
        "rasio_tanah_bangunan": rasio,
        "total_ruangan": total_ruangan,
    }

    if feature_cols:
        input_df = pd.DataFrame([features])[feature_cols]
    else:
        input_df = pd.DataFrame([features])

    harga_jkt = max(model.predict(input_df)[0], 0)
    result = adjust_price_regional(harga_jkt, kota_jateng, regional_factors)
    harga_jateng = result["harga_adjusted"]

    # Display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="price-card"><h3>📍 Harga di {lokasi}</h3>'
                     f'<p class="price-jkt">{format_rupiah(harga_jkt)}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="price-card"><h3>🌍 Estimasi di {kota_jateng}</h3>'
                     f'<p class="price-jateng">{format_rupiah(harga_jateng)}</p>'
                     f'<p style="color:#a0aec0;font-size:0.8rem">Faktor: ×{result["faktor_regional"]:.2f}</p></div>',
                     unsafe_allow_html=True)
    with col3:
        selisih = harga_jkt - harga_jateng
        st.markdown(f'<div class="price-card"><h3>💰 Selisih Harga</h3>'
                     f'<p class="price-saving">{format_rupiah(selisih)}</p>'
                     f'<p style="color:#a0aec0;font-size:0.8rem">Hemat {result["persen_selisih"]:.0f}%</p></div>',
                     unsafe_allow_html=True)

    # Tabs
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🌍 Komparasi Regional", "📊 Feature Importance", "📈 Distribusi Harga"])

    with tab1:
        st.subheader("Perbandingan Harga Antar Region")
        df_regions = compare_all_regions(harga_jkt, regional_factors)
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ["#e74c3c" if k == "Jabodetabek" else "#3498db" for k in df_regions["Kota/Region"]]
        bars = ax.barh(df_regions["Kota/Region"], df_regions["Estimasi Harga"]/1e6, color=colors, edgecolor="white")
        ax.set_xlabel("Juta Rupiah")
        ax.set_title("Estimasi Harga — Spesifikasi Sama", fontweight="bold")
        ax.invert_yaxis()
        for bar, h in zip(bars, df_regions["Estimasi Harga"]):
            ax.text(bar.get_width()+5, bar.get_y()+bar.get_height()/2, format_rupiah(h), va="center", fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
        st.info("**💡 Cara Membaca Grafik:**\nGrafik ini menunjukkan perbandingan harga jika spesifikasi rumah Anda dibangun di Jabodetabek (warna merah) dibandingkan jika dibangun di berbagai kota di Jawa Tengah (warna biru). **Semakin pendek batang birunya, semakin murah** perkiraan harga rumah di kota tersebut.")

    with tab2:
        st.subheader(f"Feature Importance — {selected_model}")
        if hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
            feat_names = feature_cols if feature_cols else list(features.keys())
            idx = np.argsort(imp)[::-1]
            fig, ax = plt.subplots(figsize=(10, 5))
            c = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(feat_names)))[::-1]
            ax.barh([feat_names[i] for i in idx], imp[idx], color=c, edgecolor="white")
            ax.set_xlabel("Importance")
            ax.set_title("Variabel Paling Berpengaruh", fontweight="bold")
            ax.invert_yaxis()
            plt.tight_layout()
            st.pyplot(fig)
            st.info(f"**💡 Cara Membaca Grafik:**\nGrafik ini menunjukkan **faktor apa saja yang paling menentukan harga properti** menurut model kecerdasan buatan ({selected_model}). **Semakin panjang batangnya ke kanan**, semakin besar pengaruh faktor tersebut (seperti Luas Bangunan atau Luas Tanah) terhadap naik-turunnya harga rumah.")
        else:
            st.info("Linear Regression tidak memiliki feature importance. Pilih Random Forest atau XGBoost.")

    with tab3:
        st.subheader("Distribusi Harga di Dataset")
        if df_processed is not None and "price_in_rp" in df_processed.columns:
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            axes[0].hist(df_processed["price_in_rp"], bins=50, color="#2ecc71", edgecolor="white", alpha=0.85)
            axes[0].axvline(x=harga_jkt, color="red", linestyle="--", lw=2, label=f"Prediksi: {format_rupiah(harga_jkt)}")
            axes[0].set_title("Distribusi Harga", fontweight="bold")
            axes[0].xaxis.set_major_formatter(plt.FuncFormatter(format_rupiah))
            axes[0].legend()
            if "city" in df_processed.columns:
                med = df_processed.groupby("city")["price_in_rp"].median().sort_values(ascending=False)
                axes[1].barh(med.index, med.values/1e6, color="#3498db", edgecolor="white")
                axes[1].set_xlabel("Median Harga (Juta Rp)")
                axes[1].set_title("Median Harga per Kota", fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig)
            st.info("**💡 Cara Membaca Grafik:**\n- **Grafik Kiri (Distribusi Harga):** Menunjukkan di kisaran harga berapa mayoritas rumah di dataset kita berkumpul. **Garis merah putus-putus** adalah posisi harga rumah Anda saat ini dibandingkan rumah lainnya.\n- **Grafik Kanan (Median Harga per Kota):** Menunjukkan nilai rata-rata tengah harga rumah di setiap kota. Ini berguna untuk melihat sekilas kota mana yang secara umum mematok harga paling tinggi atau paling rendah.")
        else:
            st.warning("Jalankan notebook 02 & 03 terlebih dahulu.")

    st.markdown("---")
    st.markdown(
        '<div class="footer">🏠 Geo-Price Analyzer | CRISP-DM Methodology | '
        'Komparasi Regional Jabodetabek & Jawa Tengah<br>'
        'Built with Streamlit, Scikit-Learn, & XGBoost</div>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
