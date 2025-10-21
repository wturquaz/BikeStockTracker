import sqlite3
from datetime import datetime
import hashlib

def upgrade_database():
    conn = sqlite3.connect('stok_takip.db')
    cursor = conn.cursor()
    
    try:
        # 1. Ürün tablosuna barkod alanı ekle (önce UNIQUE olmadan)
        print("Ürün tablosuna barkod alanı ekleniyor...")
        try:
            cursor.execute("ALTER TABLE urun ADD COLUMN barkod VARCHAR(100)")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Barkod sütunu zaten mevcut, atlaniyor...")
            else:
                raise e

        # 1.1. Ürün tablosuna desi alanı ekle
        print("Ürün tablosuna desi alanı ekleniyor...")
        try:
            cursor.execute("ALTER TABLE urun ADD COLUMN desi DECIMAL(8,2) DEFAULT 0.00")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Desi sütunu zaten mevcut, atlaniyor...")
            else:
                raise e
        
        # 2. Kullanıcı tablosu oluştur
        print("Kullanıcı tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kullanici (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) UNIQUE,
                sifre_hash VARCHAR(255) NOT NULL,
                tam_ad VARCHAR(100),
                rol VARCHAR(20) DEFAULT 'user', -- admin, user, viewer
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        ''')
        
        # 3. İşlem geçmişi tablosuna kullanıcı bilgisi ekle
        print("İşlem geçmişi tablosuna kullanıcı bilgisi ekleniyor...")
        try:
            cursor.execute("ALTER TABLE islem_gecmisi ADD COLUMN kullanici_id INTEGER")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("kullanici_id sütunu zaten mevcut, atlaniyor...")
            else:
                raise e
                
        try:
            cursor.execute("ALTER TABLE islem_gecmisi ADD COLUMN kullanici_adi VARCHAR(50)")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("kullanici_adi sütunu zaten mevcut, atlaniyor...")
            else:
                raise e
        
        # 4. Varsayılan admin kullanıcı oluştur
        print("Varsayılan admin kullanıcısı oluşturuluyor...")
        admin_password = "admin123"  # Değiştirilmesi gerekir
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT OR IGNORE INTO kullanici 
            (kullanici_adi, email, sifre_hash, tam_ad, rol, aktif, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@bikestock.com', password_hash, 'Sistem Yöneticisi', 'admin', 1, datetime.now()))
        
        # 5. Mevcut ürünlere örnek barkodlar ekle (sadece boş olanlara)
        print("Mevcut ürünlere örnek barkodlar ekleniyor...")
        cursor.execute("SELECT id FROM urun WHERE barkod IS NULL OR barkod = ''")
        urun_ids = cursor.fetchall()
        
        for urun_id in urun_ids:
            barkod = f"BK{urun_id[0]:06d}"  # BK000001 formatında
            cursor.execute("UPDATE urun SET barkod = ? WHERE id = ?", (barkod, urun_id[0]))
        
        # 6. Barkod için unique index oluştur
        print("Barkod için unique index oluşturuluyor...")
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_urun_barkod ON urun(barkod)")
        except sqlite3.IntegrityError:
            print("Barkod indexi oluşturulurken hata, devam ediliyor...")
        
        # 7. Stok çıkış fişi tabloları oluştur
        print("Stok çıkış fişi tabloları oluşturuluyor...")
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stok_cikis_fis_detay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fis_id INTEGER NOT NULL,
                urun_id INTEGER NOT NULL,
                urun_adi VARCHAR(200),
                cikis_adedi INTEGER NOT NULL,
                birim_desi DECIMAL(8,2),
                toplam_desi DECIMAL(8,2),
                kargo_firmasi VARCHAR(100),
                FOREIGN KEY (fis_id) REFERENCES stok_cikis_fis (id),
                FOREIGN KEY (urun_id) REFERENCES urun (id)
            )
        ''')
        
        # 8. Kargo firmaları tablosu oluştur
        print("Kargo firmaları tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kargo_firmasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firma_adi VARCHAR(100) NOT NULL UNIQUE,
                aktif BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Varsayılan kargo firmalarını ekle
        cursor.execute("SELECT COUNT(*) FROM kargo_firmasi")
        if cursor.fetchone()[0] == 0:
            kargo_firmalari = [
                'Yurtiçi Kargo', 'MNG Kargo', 'Aras Kargo', 'PTT Kargo', 'Sürat Kargo',
                'UPS Kargo', 'DHL', 'TNT', 'Horoz Lojistik', 'Trendyol Express'
            ]
            
            for firma in kargo_firmalari:
                cursor.execute('INSERT INTO kargo_firmasi (firma_adi) VALUES (?)', (firma,))
        
        conn.commit()
        print("Veritabanı güncelleme başarıyla tamamlandı!")
        
        # Güncellenen şemayı göster
        print("\n=== Güncellenmiş Tablo Şemaları ===")
        
        tables = ['urun', 'kullanici', 'islem_gecmisi']
        for table in tables:
            print(f"\n{table.upper()} tablosu:")
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            for col in columns:
                nullable = "NULL" if not col[3] else "NOT NULL"
                primary = " PRIMARY KEY" if col[5] else ""
                print(f"  - {col[1]} ({col[2]}) {nullable}{primary}")
        
        # Test verileri göster
        print("\n=== Test Verileri ===")
        cursor.execute("SELECT id, urun_adi, barkod FROM urun LIMIT 3")
        urunler = cursor.fetchall()
        print("\nÜrünler (barkod ile):")
        for urun in urunler:
            print(f"  ID: {urun[0]}, Ürün: {urun[1]}, Barkod: {urun[2]}")
            
        cursor.execute("SELECT kullanici_adi, email, rol FROM kullanici")
        kullanicilar = cursor.fetchall()
        print("\nKullanıcılar:")
        for kullanici in kullanicilar:
            print(f"  {kullanici[0]} ({kullanici[1]}) - Rol: {kullanici[2]}")
            
    except sqlite3.Error as e:
        print(f"Veritabanı hatası: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()