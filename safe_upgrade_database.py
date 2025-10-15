#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
from datetime import datetime
import os

def safe_database_upgrade():
    """Mevcut verileri koruyarak veritabanını günceller"""
    
    db_path = 'stok_takip.db'
    
    # Eğer veritabanı yoksa sıfırdan oluştur
    if not os.path.exists(db_path):
        print("Veritabanı bulunamadı, sıfırdan oluşturuluyor...")
        create_fresh_database()
        return
    
    print("Mevcut veritabanı güncelleniyor (veriler korunuyor)...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Mevcut tabloları kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Mevcut tablolar: {existing_tables}")
        
        # Eksik tabloları oluştur
        if 'kullanici' not in existing_tables:
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
            
            # Admin kullanıcı ekle
            admin_password = "admin123"
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO kullanici 
                (kullanici_adi, email, sifre_hash, tam_ad, rol, aktif, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@bikestock.com', password_hash, 'Sistem Yöneticisi', 'admin', 1, datetime.now()))
            
            print("✅ Admin kullanıcı oluşturuldu: admin/admin123")
        
        # Eksik kolonları ekle
        if 'urun' in existing_tables:
            # Barkod kolonu var mı kontrol et
            cursor.execute("PRAGMA table_info(urun)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'barkod' not in columns:
                print("Ürün tablosuna barkod kolonu ekleniyor...")
                cursor.execute("ALTER TABLE urun ADD COLUMN barkod VARCHAR(100)")
                
                # Mevcut ürünlere barkod ekle
                cursor.execute("SELECT id FROM urun")
                urun_ids = cursor.fetchall()
                for urun_id in urun_ids:
                    barkod = f"BK{urun_id[0]:06d}"
                    cursor.execute("UPDATE urun SET barkod = ? WHERE id = ?", (barkod, urun_id[0]))
                
                print(f"✅ {len(urun_ids)} ürüne barkod eklendi")
        
        # İşlem geçmişi tablosunu güncelle
        if 'islem_gecmisi' in existing_tables:
            cursor.execute("PRAGMA table_info(islem_gecmisi)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'kullanici_id' not in columns:
                cursor.execute("ALTER TABLE islem_gecmisi ADD COLUMN kullanici_id INTEGER")
                print("✅ İşlem geçmişine kullanici_id eklendi")
                
            if 'kullanici_adi' not in columns:
                cursor.execute("ALTER TABLE islem_gecmisi ADD COLUMN kullanici_adi VARCHAR(50)")
                print("✅ İşlem geçmişine kullanici_adi eklendi")
        
        # Eksik depolar ekle (varsa ekleme)
        if 'depo' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM depo")
            depo_count = cursor.fetchone()[0]
            
            if depo_count == 0:
                print("Varsayılan depolar ekleniyor...")
                depolar = [
                    ('Ana Depo', 'Merkez Lokasyon'),
                    ('Satış Mağazası', 'Şehir Merkezi'),
                    ('Online Satış', 'E-ticaret')
                ]
                
                for depo in depolar:
                    cursor.execute('INSERT INTO depo (depo_adi, lokasyon) VALUES (?, ?)', depo)
                print("✅ Varsayılan depolar eklendi")
        
        conn.commit()
        
        # Özet bilgi
        cursor.execute("SELECT COUNT(*) FROM urun")
        urun_sayisi = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM kullanici")
        kullanici_sayisi = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM depo")
        depo_sayisi = cursor.fetchone()[0]
        
        print(f"\n✅ Veritabanı güncelleme tamamlandı!")
        print(f"📦 Ürün sayısı: {urun_sayisi}")
        print(f"👤 Kullanıcı sayısı: {kullanici_sayisi}")
        print(f"🏢 Depo sayısı: {depo_sayisi}")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_fresh_database():
    """Yeni veritabanı oluşturur"""
    print("Sıfırdan veritabanı oluşturuluyor...")
    
    db_path = 'stok_takip.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Depo tablosu
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
        # Depolar
        depolar = [
            ('Ana Depo', 'Merkez Lokasyon'),
            ('Satış Mağazası', 'Şehir Merkezi'),
            ('Online Satış', 'E-ticaret')
        ]
        
        for depo in depolar:
            cursor.execute('INSERT INTO depo (depo_adi, lokasyon) VALUES (?, ?)', depo)
        
        # Admin kullanıcı
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
        print("✅ Yeni veritabanı oluşturuldu!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    safe_database_upgrade()