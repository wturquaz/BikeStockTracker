#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Birleşik Stok İşlem Sistemi - Veritabanı Şeması ve Geçiş Scripti
Bu script, stok giriş/çıkış işlemlerini tek bir sistemde birleştirmek için
gerekli veritabanı değişikliklerini yapar.
"""

import sqlite3
import os
from datetime import datetime

def create_unified_stock_system():
    """Birleşik stok işlem sistemi için veritabanı değişikliklerini yapar"""
    
    db_path = 'stok_takip.db'
    
    # Veritabanı dosyası var mı kontrol et
    if not os.path.exists(db_path):
        print("❌ Hata: stok_takip.db dosyası bulunamadı!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Birleşik stok işlem sistemi oluşturuluyor...")
        
        # 1. İşlem tipleri tablosu oluştur
        print("📋 İşlem tipleri tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS islem_tipi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kod VARCHAR(20) NOT NULL UNIQUE,
                ad VARCHAR(50) NOT NULL,
                aciklama TEXT,
                stok_yonu INTEGER NOT NULL, -- +1: Artış, -1: Azalış, 0: Transfer/Sayım
                renk VARCHAR(20) DEFAULT 'primary',
                ikon VARCHAR(30) DEFAULT 'arrow-up-down',
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Varsayılan işlem tiplerini ekle
        print("📝 Varsayılan işlem tipleri ekleniyor...")
        islem_tipleri = [
            ('ALIS', 'Alış/Satın Alma', 'Tedarikçiden alınan ürünler - Stok artar', 1, 'success', 'cart-plus'),
            ('SATIS', 'Satış', 'Müşterilere satılan ürünler - Stok azalır', -1, 'danger', 'cart-dash'),
            ('IADE', 'İade', 'Müşterilerden iade edilen ürünler - Stok artar', 1, 'warning', 'arrow-counterclockwise'),
            ('TRANSFER', 'Depo Transferi', 'Depolar arası ürün transferi', 0, 'info', 'arrow-left-right'),
            ('SAYIM', 'Sayım Düzeltmesi', 'Stok sayımı sonucu düzeltme', 0, 'secondary', 'calculator'),
            ('URETIM', 'Üretim', 'Üretim sonucu stok girişi - Stok artar', 1, 'primary', 'gear'),
            ('FIRE', 'Fire/Kayıp', 'Fire, kayıp, hasar - Stok azalır', -1, 'dark', 'exclamation-triangle')
        ]
        
        for tip in islem_tipleri:
            cursor.execute('''
                INSERT OR IGNORE INTO islem_tipi (kod, ad, aciklama, stok_yonu, renk, ikon)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', tip)
        
        # 3. Birleşik stok işlem tablosu oluştur
        print("📊 Birleşik stok işlem tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stok_islem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fis_no VARCHAR(50) NOT NULL UNIQUE,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
                islem_tipi_id INTEGER NOT NULL,
                depo_id INTEGER NOT NULL,
                hedef_depo_id INTEGER, -- Transfer işlemleri için
                aciklama TEXT,
                toplam_urun_adedi INTEGER DEFAULT 0,
                toplam_adet INTEGER DEFAULT 0,
                toplam_desi DECIMAL(10,2) DEFAULT 0,
                kullanici_id INTEGER,
                kullanici_adi VARCHAR(50),
                durum VARCHAR(20) DEFAULT 'TAMAMLANDI',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (islem_tipi_id) REFERENCES islem_tipi (id),
                FOREIGN KEY (depo_id) REFERENCES depo (id),
                FOREIGN KEY (hedef_depo_id) REFERENCES depo (id),
                FOREIGN KEY (kullanici_id) REFERENCES kullanici (id)
            )
        ''')
        
        # 4. Birleşik stok işlem detay tablosu oluştur
        print("📋 Stok işlem detay tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stok_islem_detay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                islem_id INTEGER NOT NULL,
                urun_id INTEGER NOT NULL,
                urun_adi VARCHAR(200),
                adet INTEGER NOT NULL,
                urun_adedi INTEGER DEFAULT 1,
                birim_desi DECIMAL(8,2),
                toplam_desi DECIMAL(8,2),
                birim_fiyat DECIMAL(10,2), -- Alış/satış fiyatı için
                toplam_fiyat DECIMAL(10,2),
                kargo_firmasi_id INTEGER,
                notlar TEXT,
                FOREIGN KEY (islem_id) REFERENCES stok_islem (id),
                FOREIGN KEY (urun_id) REFERENCES urun (id),
                FOREIGN KEY (kargo_firmasi_id) REFERENCES kargo_firmasi (id)
            )
        ''')
        
        # 5. Fiş no için sequence tablosu oluştur
        print("🔢 Fiş numarası sequence tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fis_sequence (
                islem_tipi_kod VARCHAR(20) PRIMARY KEY,
                son_no INTEGER DEFAULT 0,
                prefix VARCHAR(10) DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Varsayılan sequence değerlerini ekle
        for tip in ['ALIS', 'SATIS', 'IADE', 'TRANSFER', 'SAYIM', 'URETIM', 'FIRE']:
            cursor.execute('''
                INSERT OR IGNORE INTO fis_sequence (islem_tipi_kod, prefix)
                VALUES (?, ?)
            ''', (tip, tip[:2]))
        
        # 6. Stok hesaplama için trigger oluştur
        print("⚡ Stok hesaplama trigger'ları oluşturuluyor...")
        
        # Stok işlem ekleme trigger'ı
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS tr_stok_islem_detay_after_insert
            AFTER INSERT ON stok_islem_detay
            BEGIN
                -- Stok güncelle
                UPDATE urun_stok 
                SET miktar = miktar + (
                    NEW.adet * (
                        SELECT stok_yonu 
                        FROM islem_tipi 
                        WHERE id = (SELECT islem_tipi_id FROM stok_islem WHERE id = NEW.islem_id)
                    )
                ),
                updated_at = CURRENT_TIMESTAMP
                WHERE urun_id = NEW.urun_id 
                AND depo_id = (SELECT depo_id FROM stok_islem WHERE id = NEW.islem_id);
                
                -- Eğer stok kaydı yoksa oluştur
                INSERT OR IGNORE INTO urun_stok (urun_id, depo_id, miktar, created_at, updated_at)
                SELECT NEW.urun_id, 
                       (SELECT depo_id FROM stok_islem WHERE id = NEW.islem_id),
                       NEW.adet * (
                           SELECT stok_yonu 
                           FROM islem_tipi 
                           WHERE id = (SELECT islem_tipi_id FROM stok_islem WHERE id = NEW.islem_id)
                       ),
                       CURRENT_TIMESTAMP,
                       CURRENT_TIMESTAMP
                WHERE NOT EXISTS (
                    SELECT 1 FROM urun_stok 
                    WHERE urun_id = NEW.urun_id 
                    AND depo_id = (SELECT depo_id FROM stok_islem WHERE id = NEW.islem_id)
                );
                
                -- Transfer işlemi ise hedef depoya da ekle
                INSERT OR IGNORE INTO urun_stok (urun_id, depo_id, miktar, created_at, updated_at)
                SELECT NEW.urun_id,
                       si.hedef_depo_id,
                       NEW.adet,
                       CURRENT_TIMESTAMP,
                       CURRENT_TIMESTAMP
                FROM stok_islem si, islem_tipi it
                WHERE si.id = NEW.islem_id 
                AND it.id = si.islem_tipi_id
                AND it.kod = 'TRANSFER'
                AND si.hedef_depo_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM urun_stok 
                    WHERE urun_id = NEW.urun_id 
                    AND depo_id = si.hedef_depo_id
                );
                
                -- Transfer işlemi ise hedef depoya stok ekle
                UPDATE urun_stok 
                SET miktar = miktar + NEW.adet,
                    updated_at = CURRENT_TIMESTAMP
                WHERE urun_id = NEW.urun_id 
                AND depo_id = (
                    SELECT hedef_depo_id 
                    FROM stok_islem si, islem_tipi it
                    WHERE si.id = NEW.islem_id 
                    AND it.id = si.islem_tipi_id
                    AND it.kod = 'TRANSFER'
                    AND si.hedef_depo_id IS NOT NULL
                );
            END
        ''')
        
        # 7. View oluştur - kolay raporlama için
        print("👁️ Raporlama view'ları oluşturuluyor...")
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS v_stok_islem_rapor AS
            SELECT 
                si.id,
                si.fis_no,
                si.tarih,
                it.kod as islem_tipi_kod,
                it.ad as islem_tipi_adi,
                it.stok_yonu,
                it.renk as islem_renk,
                it.ikon as islem_ikon,
                d1.depo_adi as kaynak_depo,
                d2.depo_adi as hedef_depo,
                si.aciklama,
                si.toplam_urun_adedi,
                si.toplam_adet,
                si.toplam_desi,
                si.kullanici_adi,
                si.durum,
                si.created_at
            FROM stok_islem si
            JOIN islem_tipi it ON si.islem_tipi_id = it.id
            JOIN depo d1 ON si.depo_id = d1.id
            LEFT JOIN depo d2 ON si.hedef_depo_id = d2.id
            ORDER BY si.tarih DESC
        ''')
        
        conn.commit()
        print("✅ Birleşik stok işlem sistemi başarıyla oluşturuldu!")
        
        # Oluşturulan tabloları listele
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%islem%' OR name LIKE '%sequence%'
            ORDER BY name
        ''')
        
        print("\n📋 Oluşturulan tablolar:")
        for table in cursor.fetchall():
            print(f"   • {table[0]}")
        
        # İşlem tiplerini listele
        cursor.execute('SELECT kod, ad, stok_yonu, renk FROM islem_tipi ORDER BY id')
        print("\n🏷️ İşlem tipleri:")
        for tip in cursor.fetchall():
            yon = "+" if tip[2] == 1 else "-" if tip[2] == -1 else "↔"
            print(f"   • {tip[0]} - {tip[1]} ({yon}) [{tip[3]}]")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Birleşik Stok İşlem Sistemi Kurulumu")
    print("=" * 50)
    
    if create_unified_stock_system():
        print("\n🎉 Kurulum tamamlandı!")
        print("\nŞimdi yapılacaklar:")
        print("1. Flask uygulamasında yeni route'ları ekleyin")
        print("2. Birleşik stok işlem template'ini oluşturun")
        print("3. Mevcut stok_girisi ve stok_cikisi route'larını güncelleyin")
    else:
        print("\n💥 Kurulum başarısız!")