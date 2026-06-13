import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import warnings

# Birinci dosyada yazdığımız fonksiyonu VS Code üzerinden buraya bağlıyoruz
from feature_engineering import create_features 

warnings.filterwarnings('ignore')

print("🚀 Lokal Bilgisayarda Gelişmiş XGBoost Modeli Başlatılıyor...")

def mape_hesapla(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if np.sum(mask) == 0: return 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

# VS Code Klasör ve Dosya Yapısı Ayarı
girdi_dosyasi = "Desi_talep.xlsx"
cikti_klasoru = "tahmin_ciktisi"
cikti_dosyasi = os.path.join(cikti_klasoru, "Tahminlenen_Talep.xlsx")

# Eğer 'tahmin_ciktisi' klasörü bilgisayarda yoksa otomatik oluştursun (Hata vermemesi için)
if not os.path.exists(cikti_klasoru):
    os.makedirs(cikti_klasoru)

# Dosya kontrolü
if not os.path.exists(girdi_dosyasi):
    # Eğer kod bir üst dizinden çalıştırılıyorsa tahmini yolu dene
    if os.path.exists(os.path.join("tahmin", "Desi_talep.xlsx")):
        girdi_dosyasi = os.path.join("tahmin", "Desi_talep.xlsx")
        cikti_dosyasi = os.path.join("tahmin", "tahmin_ciktisi", "Tahminlenen_Talep.xlsx")
    else:
        print(f"\n❌ HATA: '{girdi_dosyasi}' dosyası bulunamadı!")
        print("💡 Çözüm: Lütfen 'Desi_talep.xlsx' dosyasını kodun olduğu dizine koyun.")
        sys.exit()

print(f"🎯 Veri Seti Okunuyor: '{girdi_dosyasi}'")
df = pd.read_excel(girdi_dosyasi)
df['Tarih'] = pd.to_datetime(df['Tarih'])

# Tüm rotaları belirle ve zaman serisindeki eksik günleri doldur
rotalar_global = df.groupby(['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi']).size().reset_index()
tum_tarihler = pd.date_range(start=df['Tarih'].min(), end=df['Tarih'].max(), freq='D')

genisletilmis_veri = []
for _, row in rotalar_global.iterrows():
    cikis = row['Çıkış Transfer Merkezi']
    varis = row['Varış Transfer Merkezi']
    temp_df = pd.DataFrame({'Tarih': tum_tarihler})
    temp_df['Çıkış Transfer Merkezi'] = cikis
    temp_df['Varış Transfer Merkezi'] = varis
    genisletilmis_veri.append(temp_df)
    
base_df = pd.concat(genisletilmis_veri, ignore_index=True)
df_merged = pd.merge(base_df, df, on=['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi', 'Tarih'], how='left')
df_merged['Toplam Desi'] = df_merged['Toplam Desi'].fillna(0)
df_merged = df_merged.sort_values(by=['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi', 'Tarih']).reset_index(drop=True)

# Geçmiş Gecikme (Lag) ve Hareketli Ortalama Hesaplamaları
for lag in [7, 14, 21, 28]:
    df_merged[f'lag_{lag}'] = df_merged.groupby(['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi'])['Toplam Desi'].shift(lag)
for window in [7, 14]:
    df_merged[f'rolling_mean_{window}'] = df_merged.groupby(['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi'])['Toplam Desi'].shift(1).rolling(window=window).mean()

# feature_engineering.py'den gelen fonksiyonu çağırıyoruz
df_merged = create_features(df_merged)
df_features = df_merged.dropna().reset_index(drop=True)

# Model Eğitimi (XGBoost)
print("-> Model Eğitim Aşamasına Geçildi...")
son_tarih = df_features['Tarih'].max()
tren_kesim_tarihi = son_tarih - pd.Timedelta(days=7)

train_data = df_features[df_features['Tarih'] <= tren_kesim_tarihi]
val_data = df_features[df_features['Tarih'] > tren_kesim_tarihi]

X_cols = [f'lag_{i}' for i in [7, 14, 21, 28]] + ['rolling_mean_7', 'rolling_mean_14', 
          'ay', 'gun', 'day_of_week', 'is_weekend', 'is_month_start', 'is_month_end', 'is_holiday', 'is_discount_season']

X_train, y_train = train_data[X_cols], train_data['Toplam Desi']
X_val, y_val = val_data[X_cols], val_data['Toplam Desi']

xgb_model = xgb.XGBRegressor(n_estimators=150, learning_rate=0.06, max_depth=7, subsample=0.8, random_state=42)
xgb_model.fit(X_train, y_train)

val_data['xgb_pred'] = xgb_model.predict(X_val)
print(f"   [Doğrulama Skoru] MAE: {mean_absolute_error(y_val, val_data['xgb_pred']):.2f} | MAPE: {mape_hesapla(y_val, val_data['xgb_pred']):.2f}%")

# Dinamik Gelecek Tahmin Simülasyonu
print("-> Gelecek 30 Günlük Dinamik Tahmin Döngüsü Çalıştırılıyor...")
gelecek_gunler = 30
gelecek_tarihler = pd.date_range(start=son_tarih + pd.Timedelta(days=1), periods=gelecek_gunler, freq='D')
nihai_tahmin_listesi = []

for _, row in rotalar_global.iterrows():
    cikis = row['Çıkış Transfer Merkezi']
    varis = row['Varış Transfer Merkezi']
    rota_df = df_features[(df_features['Çıkış Transfer Merkezi'] == cikis) & (df_features['Varış Transfer Merkezi'] == varis)].copy()
    
    for yeni_tarih in gelecek_tarihler:
        yeni_satir = pd.DataFrame({'Tarih': [yeni_tarih], 'Çıkış Transfer Merkezi': [cikis], 'Varış Transfer Merkezi': [varis]})
        yeni_satir = create_features(yeni_satir)
        
        yeni_satir['lag_7'] = rota_df['Toplam Desi'].iloc[-7] if len(rota_df) >= 7 else rota_df['Toplam Desi'].mean()
        yeni_satir['lag_14'] = rota_df['Toplam Desi'].iloc[-14] if len(rota_df) >= 14 else rota_df['Toplam Desi'].mean()
        yeni_satir['lag_21'] = rota_df['Toplam Desi'].iloc[-21] if len(rota_df) >= 21 else rota_df['Toplam Desi'].mean()
        yeni_satir['lag_28'] = rota_df['Toplam Desi'].iloc[-28] if len(rota_df) >= 28 else rota_df['Toplam Desi'].mean()
        
        yeni_satir['rolling_mean_7'] = rota_df['Toplam Desi'].iloc[-7:].mean()
        yeni_satir['rolling_mean_14'] = rota_df['Toplam Desi'].iloc[-14:].mean()
        
        pred_df = yeni_satir[X_cols]
        xgb_pred = xgb_model.predict(pred_df)[0]
        
        trend_pred = yeni_satir['rolling_mean_7'].values[0] * 0.94 + yeni_satir['lag_7'].values[0] * 0.06
        nihai_tahmin = max(0, (xgb_pred * 0.65) + (trend_pred * 0.35))
        
        # Muhammed Bey'in Risk ve Hava Durumu Katsayıları
        emniyet_katsayisi = 1.05 
        hava_durumu_risk_katsayisi = 1.08 if yeni_tarih.month in [12, 1, 2] else 1.00
        nihai_tahmin = nihai_tahmin * emniyet_katsayisi * hava_durumu_risk_katsayisi
        
        yeni_satir['Toplam Desi'] = nihai_tahmin
        yeni_satir['Tahmini Desi'] = nihai_tahmin
        
        rota_df = pd.concat([rota_df, yeni_satir], ignore_index=True)
        nihai_tahmin_listesi.append(yeni_satir)

# Sonuçları Kaydetme
nihai_cikti = pd.concat(nihai_tahmin_listesi, ignore_index=True)[['Çıkış Transfer Merkezi', 'Varış Transfer Merkezi', 'Tarih', 'Tahmini Desi']]
nihai_cikti.to_excel(cikti_dosyasi, index=False)

print(f"\n🏆 BAŞARILI! Tahmin dosyası lokal olarak '{cikti_dosyasi}' yoluna kaydedildi.")