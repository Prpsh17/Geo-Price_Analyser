# 🏠 Geo-Price Analyzer

**Prediksi Harga Properti Berbasis Machine Learning dengan Komparasi Regional Jabodetabek & Jawa Tengah**

## 📋 Deskripsi & Studi Kasus

**Studi Kasus:** *Analisis Disparitas Harga dan Prediksi Nilai Properti antara Wilayah Metropolitan (Jabodetabek) dan Regional (Jawa Tengah)*.

**Latar Belakang Kasus:**
Di industri *real estate*, harga properti seringkali tidak transparan dan subyektif karena dipengaruhi banyak variabel (luas tanah, luas bangunan, lokasi, dll). Selain itu, terdapat kesenjangan (*disparitas*) harga yang cukup ekstrem antara kawasan metropolitan (Jabodetabek) dengan daerah regional (Jawa Tengah). Calon pembeli atau investor sering kesulitan menaksir harga pasar yang wajar dan membandingkan seberapa besar selisih *budget* jika mereka berinvestasi di luar ibu kota.

Aplikasi data mining **Geo-Price Analyzer** memecahkan kasus tersebut dengan menggunakan *Data Science* untuk:
1. Memprediksi harga rumah yang wajar dan objektif berdasarkan spesifikasinya menggunakan algoritma *Machine Learning*.
2. Mengkalkulasi *Regional Adjustment Factor* (Faktor Kalibrasi Regional) berbasis data nyata untuk menyajikan analisis perbandingan harga secara interaktif bagi non-profesional/masyarakat umum.

## 🎯 Tahapan Data Mining (CRISP-DM)
Proyek ini mengadopsi kerangka kerja standar industri (CRISP-DM) yang meliputi:
1. **Business Understanding:** Memahami tingginya kebutuhan akan informasi harga properti yang akurat. Tujuannya adalah membangun model cerdas untuk memprediksi estimasi harga yang wajar dan menganalisis disparitas (*Regional Adjustment Factor*) antara kota metropolitan dan daerah, sehingga dapat membantu pembeli dan investor mengambil keputusan.
2. **Data Understanding:** Melakukan *Exploratory Data Analysis* (EDA) pada kumpulan data (dataset) properti untuk memahami karakteristik data. Mencakup analisis distribusi harga, korelasi luas tanah/bangunan terhadap harga, serta deteksi anomali (*outliers*).
3. **Data Preparation:** Tahapan pembersihan data (*cleaning*), penanganan nilai kosong (*missing values*), dan pembentukan fitur baru (*feature engineering*) seperti rasio tanah/bangunan agar data mentah siap dipelajari oleh mesin.
4. **Modeling:** Melatih dan membandingkan performa beberapa algoritma *Machine Learning* (*Linear Regression, Random Forest, XGBoost*) untuk mendapatkan model dengan akurasi prediksi tertinggi (evaluasi melalui R², RMSE, MAE).
5. **Deployment & Visualisasi:** Men-*deploy* model terbaik ke dalam sebuah *dashboard* berbasis *web* interaktif menggunakan Streamlit. Tahapan ini menyajikan visualisasi perbandingan harga secara *real-time*, *feature importance* (faktor paling berpengaruh), dan distribusi harga dalam bentuk *user-interface* yang mudah dipahami (*layman terms*).

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
