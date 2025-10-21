#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

def add_missing_columns():
    """Eksik kolonları ekle"""
    
    conn = sqlite3.connect('stok_takip.db')
    cursor = conn.cursor()
    
    try:
        print("Veritabanı kolonları kontrol ediliyor...")
        
        # Ürün tablosunu kontrol et
        cursor.execute("PRAGMA table_info(urun)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Mevcut ürün tablosu kolonları: {columns}")
        
        # Desi kolonu yoksa ekle
        if 'desi' not in columns:
            print("Desi kolonu ekleniyor...")
            cursor.execute("ALTER TABLE urun ADD COLUMN desi DECIMAL(8,2) DEFAULT 0.00")
            print("✅ Desi kolonu eklendi")
        else:
            print("✅ Desi kolonu zaten mevcut")
        
        # Barkod kolonu yoksa ekle
        if 'barkod' not in columns:
            print("Barkod kolonu ekleniyor...")
            cursor.execute("ALTER TABLE urun ADD COLUMN barkod VARCHAR(100)")
            
            # Mevcut ürünlere barkod ekle
            cursor.execute("SELECT id FROM urun")
            urun_ids = cursor.fetchall()
            for urun_id in urun_ids:
                barkod = f"BK{urun_id[0]:06d}"
                cursor.execute("UPDATE urun SET barkod = ? WHERE id = ?", (barkod, urun_id[0]))
            
            print(f"✅ Barkod kolonu eklendi ve {len(urun_ids)} ürüne barkod atandı")
        else:
            print("✅ Barkod kolonu zaten mevcut")
            
        # Kargo firması tablosu kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kargo_firmasi'")
        if not cursor.fetchone():
            print("Kargo firması tablosu oluşturuluyor...")
            cursor.execute('''
                CREATE TABLE kargo_firmasi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firma_adi VARCHAR(100) NOT NULL UNIQUE,
                    kisa_adi VARCHAR(20),
                    telefon VARCHAR(20),
                    website VARCHAR(100),
                    aktif BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Varsayılan kargo firmaları ekle
            kargo_firmalari = [
                ('Aras Kargo', 'ARAS', '444 2727', 'www.araskargo.com.tr'),
                ('MNG Kargo', 'MNG', '444 0606', 'www.mngkargo.com.tr'),
                ('PTT Kargo', 'PTT', '444 1788', 'www.pttpost.com'),
                ('Yurtiçi Kargo', 'YURTİÇİ', '444 9999', 'www.yurticikargo.com'),
                ('UPS Kargo', 'UPS', '444 8877', 'www.ups.com.tr'),
                ('Diğer', 'DİĞER', '', '')
            ]
            
            for firma in kargo_firmalari:
                cursor.execute('''
                    INSERT INTO kargo_firmasi (firma_adi, kisa_adi, telefon, website)
                    VALUES (?, ?, ?, ?)
                ''', firma)
            
            print("✅ Kargo firması tablosu oluşturuldu")
        else:
            print("✅ Kargo firması tablosu zaten mevcut")
        
        # Stok çıkış fişi detay tablosunu kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stok_cikis_fis_detay'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(stok_cikis_fis_detay)")
            detay_columns = [col[1] for col in cursor.fetchall()]
            
            if 'kargo_firmasi_id' not in detay_columns:
                print("Fiş detay tablosuna kargo_firmasi_id kolonu ekleniyor...")
                cursor.execute("ALTER TABLE stok_cikis_fis_detay ADD COLUMN kargo_firmasi_id INTEGER REFERENCES kargo_firmasi(id)")
                print("✅ Kargo firmasi_id kolonu eklendi")
        
        # Ayarlar tablosunu kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ayarlar'")
        if not cursor.fetchone():
            print("Ayarlar tablosu oluşturuluyor...")
            cursor.execute('''
                CREATE TABLE ayarlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anahtar VARCHAR(100) NOT NULL UNIQUE,
                    deger TEXT,
                    aciklama TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Ayarlar tablosu oluşturuldu")
        else:
            print("✅ Ayarlar tablosu zaten mevcut")
        
        # Stok çıkış fişi tablosunu kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stok_cikis_fis'")
        if not cursor.fetchone():
            print("Stok çıkış fişi tablosu oluşturuluyor...")
            cursor.execute('''
                CREATE TABLE stok_cikis_fis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fis_no VARCHAR(50) NOT NULL UNIQUE,
                    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
                    depo_id INTEGER NOT NULL,
                    aciklama TEXT,
                    toplam_urun_adedi INTEGER DEFAULT 0,
                    toplam_adet INTEGER DEFAULT 0,
                    kullanici_id INTEGER,
                    kullanici_adi VARCHAR(50),
                    durum VARCHAR(20) DEFAULT 'TAMAMLANDI',
                    FOREIGN KEY (depo_id) REFERENCES depo (id),
                    FOREIGN KEY (kullanici_id) REFERENCES kullanici (id)
                )
            ''')
            print("✅ Stok çıkış fişi tablosu oluşturuldu")
        else:
            print("✅ Stok çıkış fişi tablosu zaten mevcut")
        
        # Stok çıkış fişi detay tablosunu kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stok_cikis_fis_detay'")
        if not cursor.fetchone():
            print("Stok çıkış fişi detay tablosu oluşturuluyor...")
            cursor.execute('''
                CREATE TABLE stok_cikis_fis_detay (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fis_id INTEGER NOT NULL,
                    urun_id INTEGER NOT NULL,
                    urun_adi VARCHAR(200),
                    cikis_adedi INTEGER NOT NULL,
                    birim_desi DECIMAL(8,2),
                    toplam_desi DECIMAL(8,2),
                    kargo_firmasi_id INTEGER,
                    FOREIGN KEY (fis_id) REFERENCES stok_cikis_fis (id),
                    FOREIGN KEY (urun_id) REFERENCES urun (id),
                    FOREIGN KEY (kargo_firmasi_id) REFERENCES kargo_firmasi (id)
                )
            ''')
            print("✅ Stok çıkış fişi detay tablosu oluşturuldu")
        else:
            print("✅ Stok çıkış fişi detay tablosu zaten mevcut")
            # Kargo firmasi_id kolonu var mı kontrol et
            cursor.execute("PRAGMA table_info(stok_cikis_fis_detay)")
            detay_columns = [col[1] for col in cursor.fetchall()]
            
            if 'kargo_firmasi_id' not in detay_columns:
                print("Fiş detay tablosuna kargo_firmasi_id kolonu ekleniyor...")
                cursor.execute("ALTER TABLE stok_cikis_fis_detay ADD COLUMN kargo_firmasi_id INTEGER REFERENCES kargo_firmasi(id)")
                print("✅ Kargo firmasi_id kolonu eklendi")
        
        conn.commit()
        print("\n✅ Tüm eksik kolonlar başarıyla eklendi!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()