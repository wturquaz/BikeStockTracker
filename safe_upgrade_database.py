import sqlite3
from datetime import datetime
import hashlib

def upgrade_database():
    """Database'i güvenli şekilde güncelle - Render.com için"""
    db_path = 'stok_takip.db'
    print(f"Database upgrade başlatılıyor: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Foreign key desteğini aç
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("📋 Temel tabloları oluşturuluyor...")
        
        # Depo tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS depo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depo_adi VARCHAR(100) NOT NULL UNIQUE,
                adres TEXT,
                telefon VARCHAR(20),
                email VARCHAR(100),
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ürün tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urun (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi VARCHAR(200) NOT NULL,
                jant_ebati VARCHAR(50),
                lastik_ebati VARCHAR(100),
                barkod VARCHAR(100) UNIQUE,
                desi DECIMAL(8,2) DEFAULT 0.00,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Kullanıcı tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kullanici (
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
        
        # Ürün stok tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urun_stok (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                depo_id INTEGER NOT NULL,
                miktar INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (urun_id) REFERENCES urun (id),
                FOREIGN KEY (depo_id) REFERENCES depo (id),
                UNIQUE(urun_id, depo_id)
            )
        ''')
        
        # İşlem geçmişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS islem_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
                islem_tipi VARCHAR(50),
                urun_id INTEGER,
                depo_id INTEGER,
                hedef_depo_id INTEGER,
                eski_deger VARCHAR(100),
                yeni_deger VARCHAR(100),
                urun_bilgisi TEXT,
                kullanici_id INTEGER,
                kullanici_adi VARCHAR(50),
                FOREIGN KEY (urun_id) REFERENCES urun (id),
                FOREIGN KEY (depo_id) REFERENCES depo (id),
                FOREIGN KEY (kullanici_id) REFERENCES kullanici (id)
            )
        ''')
        
        # Kargo firmasi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kargo_firmasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firma_adi VARCHAR(100) NOT NULL UNIQUE,
                aktif BOOLEAN DEFAULT 1,
                oluşturma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Stok çıkış fişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stok_cikis_fis (
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
        
        # Stok çıkış fişi detay tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stok_cikis_fis_detay (
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
        
        # Ayarlar tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ayarlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anahtar VARCHAR(100) NOT NULL UNIQUE,
                deger TEXT,
                aciklama TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        print("📦 Varsayılan veriler oluşturuluyor...")
        
        # Varsayılan admin kullanıcı
        admin_password = "admin123"
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT OR IGNORE INTO kullanici 
            (kullanici_adi, email, sifre_hash, tam_ad, rol, aktif, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@bikestock.com', password_hash, 'Sistem Yöneticisi', 'admin', 1, datetime.now()))
        
        # Varsayılan depo
        cursor.execute('''
            INSERT OR IGNORE INTO depo (depo_adi, aktif)
            VALUES ('Ana Depo', 1)
        ''')
        
        # Varsayılan kargo firmaları
        kargo_firmalari = [
            'Yurtiçi Kargo', 'Aras Kargo', 'MNG Kargo', 
            'PTT Kargo', 'UPS Kargo', 'Sürat Kargo'
        ]
        
        for firma in kargo_firmalari:
            cursor.execute('INSERT OR IGNORE INTO kargo_firmasi (firma_adi) VALUES (?)', (firma,))
        
        # Değişiklikleri kaydet
        conn.commit()
        
        print("✅ Database upgrade başarıyla tamamlandı!")
        
        # Tablo sayısını kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Toplam tablo sayısı: {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")
            
    except Exception as e:
        print(f"❌ Database upgrade hatası: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()