# 🏠 Geo-Price Analyzer

**Prediksi Harga Properti Berbasis Machine Learning dengan Komparasi Regional Jabodetabek & Jawa Tengah**

## 📋 Deskripsi
Aplikasi data mining yang menggunakan metodologi CRISP-DM untuk memprediksi harga properti secara objektif dan membandingkan disparitas harga antar wilayah metropolitan (Jabodetabek) dan regional (Jawa Tengah).

## 🚀 Quick Start

### 1. Aktivasi Virtual Environment
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Generate Dataset
```bash
python -m src.data_generator
```

### 3. Jalankan EDA
```bash
python -m src.eda
```

### 4. Training Model
```bash
python -m src.modeling
```

### 5. Jalankan Dashboard
```bash
streamlit run app.py
```

## 📁 Struktur Proyek
```
projek datmin/
├── .venv/                      # Virtual environment
├── data/
│   ├── raw/                    # Dataset mentah
│   └── processed/              # Dataset setelah preprocessing
├── models/                     # Model .pkl tersimpan
├── notebooks/                  # Jupyter notebooks & plot EDA
├── src/
│   ├── data_generator.py       # Generate dataset sintetis
│   ├── preprocessing.py        # Cleaning & feature engineering
│   ├── eda.py                  # Exploratory Data Analysis
│   ├── modeling.py             # Training & evaluasi model
│   └── regional_adjustment.py  # Faktor kalibrasi regional
├── app.py                      # Streamlit dashboard
├── requirements.txt            # Dependensi Python
└── README.md                   # Dokumentasi
```

## 🤖 Model
- **Linear Regression** — Baseline model
- **Random Forest** — Model utama (robust terhadap non-linearity)
- **XGBoost** — Gradient boosting model

## 📊 Metrik Evaluasi
- **R² Score** (Target > 0.80)
- **RMSE** (Root Mean Squared Error)
- **MAE** (Mean Absolute Error)

## 🌍 Regional Adjustment Factor
| Region | Faktor |
|--------|--------|
| Jabodetabek | 1.00 |
| Semarang | 0.40 |
| Solo | 0.36 |
| Jawa Tengah (Rata-rata) | 0.34 |
| Magelang | 0.30 |
| Purwokerto | 0.28 |
| Banyumas | 0.26 |

## 🛠️ Tech Stack
- **Python** (Pandas, NumPy, Scikit-Learn, XGBoost)
- **Streamlit** (Dashboard)
- **Joblib** (Model storage)
- **Matplotlib & Seaborn** (Visualisasi)
