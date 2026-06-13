import pandas as pd
import numpy as np

def create_features(df):
    """
    Nexus Nova Lojistik - Gelişmiş Talep Tahmin Modülü Özellik Mühendisliği.
    Hafta içi/sonu, ay başı/sonu, e-ticaret indirimleri ve tatil dinamiklerini ekler.
    """
    df = df.copy()
    if 'Tarih' in df.columns:
        df['Tarih'] = pd.to_datetime(df['Tarih'])
        df['ay'] = df['Tarih'].dt.month
        df['gun'] = df['Tarih'].dt.day
        df['day_of_week'] = df['Tarih'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # 1. Ay Başı ve Ay Sonu Etkileri (Finansal ve sevkiyat yoğunluk dönemleri)
        df['is_month_start'] = df['Tarih'].dt.is_month_start.astype(int)
        df['is_month_end'] = df['Tarih'].dt.is_month_end.astype(int)
        
        # 2. 2026 Genişletilmiş Resmi Tatil Takvimi
        resmi_tatiller = ['01-01', '04-23', '05-01', '05-19', '07-15', '08-30', '10-29']
        df['is_holiday'] = df['Tarih'].dt.strftime('%m-%d').isin(resmi_tatiller).astype(int)
        
        # 2026 Hareketli Dini Tatiller (Ramazan ve Kurban Bayramı Dönemleri)
        df.loc[df['Tarih'].between('2026-03-19', '2026-03-22'), 'is_holiday'] = 1
        df.loc[df['Tarih'].between('2026-05-26', '2026-05-30'), 'is_holiday'] = 1

        # 3. Büyük E-Ticaret Kampanya Dönemleri (11.11 ve Muhteşem Cuma)
        df['is_discount_season'] = 0
        # 11.11 İndirim Haftası
        df.loc[df['Tarih'].between('2026-11-08', '2026-11-14'), 'is_discount_season'] = 1
        # Kasım Sonu Black Friday Dönemi
        df.loc[df['Tarih'].between('2026-11-23', '2026-11-30'), 'is_discount_season'] = 1

    return df