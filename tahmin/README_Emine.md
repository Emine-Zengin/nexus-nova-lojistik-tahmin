# 📊 Talep Tahmini Modülü — Emine

Bu klasör, **Emine**'nin sorumluluğunda olan makine öğrenmesi tabanlı talep tahmini kodlarını ve çıktılarını barındırır.

---

## 🎯 Görev Tanımı

Ham desi talep verilerini (`Desi_talep.xlsx`) kullanarak **11-17 Mayıs 2026** haftasına ait günlük transfer merkezi bazlı talepleri tahmin etmek.

---

## 📁 Bu Klasördeki Dosyalar

```
tahmin/
├── README_Emine.md          # Bu dosya
├── tahmin_modeli.py         # Prophet + XGBoost tahmin kodu
├── feature_engineering.py   # Özellik mühendisliği (lag, hareketli ort., takvim)
└── tahmin_ciktisi/
    └── Tahminlened_Talep.xlsx  # Model çıktısı (teslim dosyası)
```

---

## 🧠 Kullanılan Yöntemler

### Prophet
- Mevsimsel bileşenleri (haftalık, aylık) otomatik yakalar
- Tatil ve özel gün etkilerini ayrı modelleyebilir
- Türkiye resmi tatilleri ve bayram dönemleri modele eklenmelidir

### XGBoost
- Gradient boosting ile doğrusal olmayan ilişkileri yakalar
- Feature importance ile hangi özelliklerin etkili olduğunu gösterir

---

## ⚙️ Özellik Mühendisliği (Feature Engineering)

Aşağıdaki özellikler modele eklenmelidir:

| Özellik | Açıklama |
|:---|:---|
| `lag_1` | 1 gün önceki talep |
| `lag_7` | 7 gün önceki talep (geçen hafta aynı gün) |
| `lag_14` | 14 gün önceki talep |
| `rolling_mean_7` | Son 7 günlük hareketli ortalama |
| `rolling_std_7` | Son 7 günlük standart sapma |
| `day_of_week` | Haftanın günü (0=Pazartesi, 6=Pazar) |
| `month` | Ay (1-12) |
| `is_weekend` | Hafta sonu mu? (0/1) |
| `is_holiday` | Resmi tatil mi? (0/1) |

---

## 📤 Çıktı Formatı

Tahmin dosyası (`Tahminlened_Talep.xlsx`) şu kolonları içermelidir:

| Çıkış Transfer Merkezi | Varış Transfer Merkezi | Tarih | Tahmin Edilen Talep (Desi) |
|:---|:---|:---|:---|
| İstanbul | Kocaeli | 2026-05-11 | 15420.5 |
| İstanbul | Ankara | 2026-05-11 | 8930.0 |
| ... | ... | ... | ... |

---

## 🚀 Kurulum

```bash
pip install pandas prophet xgboost scikit-learn openpyxl
```

---

## 📊 Model Değerlendirme Metrikleri

- **MAE** (Mean Absolute Error) — Ortalama mutlak hata
- **RMSE** (Root Mean Square Error) — Karekök ortalama kare hata
- **MAPE** (Mean Absolute Percentage Error) — Yüzde hata

Hedef: MAPE < %15

---

## 🔗 Bağımlılıklar

Bu modülün çıktısı doğrudan **Muhammed'in optimizasyon modülüne** girdi olarak verilir.
Çıktı dosyasının adı ve kolon yapısı değiştirilmemelidir.
