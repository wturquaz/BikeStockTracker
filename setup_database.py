#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
from datetime import datetime
import os

def create_complete_database():
    """Tüm tabloları sıfırdan oluşturur"""
    
    db_path = 'stok_takip.db'
    
    # Eğer veritabanı varsa sil (production'da dikkatli!)
    if os.path.exists(db_path):
        print(f"Mevcut veritabanı siliniyor: {db_path}")
        os.remove(db_path)
    
    print("Yeni veritabanı oluşturuluyor...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Depo tablosu
        print("Depo tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE depo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depo_adi VARCHAR(100) NOT NULL,
                lokasyon VARCHAR(255),
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Ürün tablosu
        print("Ürün tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE urun (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi VARCHAR(200) NOT NULL,
                jant_ebati VARCHAR(20),
                aciklama TEXT,
                barkod VARCHAR(100) UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. Ürün stok tablosu
        print("Ürün stok tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE urun_stok (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                depo_id INTEGER NOT NULL,
                stok_adedi INTEGER DEFAULT 0,
                min_stok_seviyesi INTEGER DEFAULT 0,
                max_stok_seviyesi INTEGER DEFAULT 100,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (urun_id) REFERENCES urun (id),
                FOREIGN KEY (depo_id) REFERENCES depo (id),
                UNIQUE(urun_id, depo_id)
            )
        ''')
        
        # 4. Kullanıcı tablosu
        print("Kullanıcı tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE kullanici (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) UNIQUE,
                sifre_hash VARCHAR(255) NOT NULL,
                tam_ad VARCHAR(100),
                rol VARCHAR(20) DEFAULT 'user',
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        ''')
        
        # 5. İşlem geçmişi tablosu
        print("İşlem geçmişi tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE islem_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                islem_tipi VARCHAR(50) NOT NULL,
                urun_id INTEGER,
                depo_id INTEGER,
                hedef_depo_id INTEGER,
                urun_bilgisi VARCHAR(500) NOT NULL,
                eski_deger VARCHAR(100),
                yeni_deger VARCHAR(100),
                tarih DATETIME,
                kullanici_id INTEGER,
                kullanici_adi VARCHAR(50),
                FOREIGN KEY (urun_id) REFERENCES urun (id),
                FOREIGN KEY (depo_id) REFERENCES depo (id),
                FOREIGN KEY (kullanici_id) REFERENCES kullanici (id)
            )
        ''')
        
        # Varsayılan veriler ekle
        print("Varsayılan veriler ekleniyor...")
        
        # Varsayılan depolar
        depolar = [
            ('Ana Depo', 'Merkez Lokasyon'),
            ('Satış Mağazası', 'Şehir Merkezi'),
            ('Online Satış', 'E-ticaret')
        ]
        
        for depo in depolar:
            cursor.execute('INSERT INTO depo (depo_adi, lokasyon) VALUES (?, ?)', depo)
        
        # Varsayılan admin kullanıcı
        admin_password = "admin123"
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO kullanici 
            (kullanici_adi, email, sifre_hash, tam_ad, rol, aktif, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@bikestock.com', password_hash, 'Sistem Yöneticisi', 'admin', 1, datetime.now()))
        
        # Test ürünleri
        test_urunler = [
            ('26" Dağ Bisikleti', '26', 'Yetişkin dağ bisikleti', 'BK000001'),
            ('24" Çocuk Bisikleti', '24', 'Çocuk bisikleti - mavi', 'BK000002'),
            ('28" Şehir Bisikleti', '28', 'Klasik şehir bisikleti', 'BK000003')
        ]
        
        for urun in test_urunler:
            cursor.execute('INSERT INTO urun (urun_adi, jant_ebati, aciklama, barkod) VALUES (?, ?, ?, ?)', urun)
        
        # Test stokları
        cursor.execute('INSERT INTO urun_stok (urun_id, depo_id, stok_adedi) VALUES (1, 1, 10)')
        cursor.execute('INSERT INTO urun_stok (urun_id, depo_id, stok_adedi) VALUES (2, 1, 5)')
        cursor.execute('INSERT INTO urun_stok (urun_id, depo_id, stok_adedi) VALUES (3, 1, 8)')
        
        conn.commit()
        print("✅ Veritabanı başarıyla oluşturuldu!")
        
        # Test
        cursor.execute("SELECT COUNT(*) FROM kullanici")
        kullanici_sayisi = cursor.fetchone()[0]
        print(f"👤 Kullanıcı sayısı: {kullanici_sayisi}")
        
        cursor.execute("SELECT COUNT(*) FROM urun")
        urun_sayisi = cursor.fetchone()[0]
        print(f"📦 Ürün sayısı: {urun_sayisi}")
        
        cursor.execute("SELECT COUNT(*) FROM depo")
        depo_sayisi = cursor.fetchone()[0]
        print(f"🏢 Depo sayısı: {depo_sayisi}")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_complete_database()