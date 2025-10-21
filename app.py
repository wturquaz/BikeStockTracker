# -*- coding: utf-8 -*-
"""
BikeStock - Bisiklet Stok Takip Sistemi
Depo bazlı bisiklet stoklarını takip eden Flask web uygulaması
"""

# Standard library imports
import hashlib
import os
import secrets
from datetime import datetime
from functools import wraps

# Third-party imports
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3

# Application initialization
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Database connection
def get_db_connection():
    """SQLite veritabanı bağlantısı oluşturur ve Row factory ayarlar"""
    db_path = os.path.join(os.path.dirname(__file__), 'stok_takip.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Authentication decorator
def login_required(f):
    """Kullanıcı girişi gerektiren route'lar için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes - Main pages
@app.route('/')
@login_required
def index():
    """Ana sayfa - Dashboard"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı giriş sayfası ve doğrulama"""
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        
        # Password hashing
        sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
        
        conn = get_db_connection()
        kullanici = conn.execute(
            'SELECT * FROM kullanici WHERE kullanici_adi = ? AND sifre_hash = ? AND aktif = 1',
            (kullanici_adi, sifre_hash)
        ).fetchone()
        
        if kullanici:
            # Giriş başarılı
            session['kullanici_id'] = kullanici['id']
            session['kullanici_adi'] = kullanici['kullanici_adi']
            session['rol'] = kullanici['rol']
            
            # Son giriş zamanını güncelle
            conn.execute(
                'UPDATE kullanici SET last_login = ? WHERE id = ?',
                (datetime.now(), kullanici['id'])
            )
            conn.commit()
            conn.close()
            
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'error')
            conn.close()
    
    return render_template('login.html')

# Çıkış
@app.route('/logout')
def logout():
    """Kullanıcı çıkışı"""
    session.clear()
    flash('Başarıyla çıkış yaptınız!', 'info')
    return redirect(url_for('login'))

# User management
@app.route('/sifre_degistir', methods=['GET', 'POST'])
@login_required
def sifre_degistir():
    """Kullanıcı şifre değiştirme"""
    if request.method == 'POST':
        mevcut_sifre = request.form['mevcut_sifre']
        yeni_sifre = request.form['yeni_sifre']
        yeni_sifre_tekrar = request.form['yeni_sifre_tekrar']
        
        # Validasyonlar
        if not mevcut_sifre or not yeni_sifre or not yeni_sifre_tekrar:
            flash('Tüm alanlar zorunludur!', 'error')
            return redirect(url_for('sifre_degistir'))
        
        if yeni_sifre != yeni_sifre_tekrar:
            flash('Yeni şifreler eşleşmiyor!', 'error')
            return redirect(url_for('sifre_degistir'))
        
        if len(yeni_sifre) < 6:
            flash('Yeni şifre en az 6 karakter olmalıdır!', 'error')
            return redirect(url_for('sifre_degistir'))
        
        conn = get_db_connection()
        
        # Mevcut şifre kontrolü
        mevcut_sifre_hash = hashlib.sha256(mevcut_sifre.encode()).hexdigest()
        kullanici = conn.execute(
            'SELECT * FROM kullanici WHERE id = ? AND sifre_hash = ?',
            (session['kullanici_id'], mevcut_sifre_hash)
        ).fetchone()
        
        if not kullanici:
            flash('Mevcut şifre yanlış!', 'error')
            conn.close()
            return redirect(url_for('sifre_degistir'))
        
        try:
            # Yeni şifre hash'i
            yeni_sifre_hash = hashlib.sha256(yeni_sifre.encode()).hexdigest()
            
            # Şifre güncelleme
            conn.execute(
                'UPDATE kullanici SET sifre_hash = ?, updated_at = ? WHERE id = ?',
                (yeni_sifre_hash, datetime.now(), session['kullanici_id'])
            )
            
            # İşlem geçmişine kaydet
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_bilgisi, tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?)
            ''', ('SIFRE_DEGISTIRME', f"Kullanıcı şifre değiştirdi: {session['kullanici_adi']}", 
                  datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            flash('Şifreniz başarıyla değiştirildi!', 'success')
            
        except Exception as e:
            flash(f'Şifre değiştirilirken hata oluştu: {str(e)}', 'error')
        finally:
            conn.close()
            
        return redirect(url_for('index'))
    
    return render_template('sifre_degistir.html')

# Stok listesi
@app.route('/stok')
@login_required
def stok_listesi():
    conn = get_db_connection()
    
    # Depo bilgilerini al
    depolar = conn.execute('SELECT * FROM depo WHERE aktif = 1').fetchall()
    
    # Seçili depo
    secili_depo_id = request.args.get('depo_id', '1')
    
    # Stok bilgilerini al (tüm depolar dahil)
    stoklar = conn.execute('''
        SELECT 
            u.id,
            u.urun_adi,
            u.jant_ebati,
            COALESCE(u.desi, 0.00) as desi,
            u.barkod,
            us.stok_adedi,
            d.depo_adi,
            us.depo_id
        FROM urun u
        LEFT JOIN urun_stok us ON u.id = us.urun_id AND us.depo_id = ?
        LEFT JOIN depo d ON us.depo_id = d.id
        ORDER BY u.urun_adi
    ''', (secili_depo_id,)).fetchall()
    
    # Toplam stok bilgilerini hesapla (tüm depolar)
    toplam_stoklar = conn.execute('''
        SELECT 
            u.id,
            u.urun_adi,
            COALESCE(u.desi, 0.00) as desi,
            SUM(COALESCE(us.stok_adedi, 0)) as toplam_stok,
            COUNT(us.depo_id) as depo_sayisi,
            GROUP_CONCAT(d.depo_adi || ': ' || COALESCE(us.stok_adedi, 0)) as depo_detay
        FROM urun u
        LEFT JOIN urun_stok us ON u.id = us.urun_id
        LEFT JOIN depo d ON us.depo_id = d.id
        GROUP BY u.id, u.urun_adi
        ORDER BY u.urun_adi
    ''').fetchall()
    
    # Seçili depo bilgisi
    secili_depo = conn.execute('SELECT * FROM depo WHERE id = ?', (secili_depo_id,)).fetchone()
    
    # Seçili depodaki toplam istatistikler
    depo_istatistik = conn.execute('''
        SELECT 
            COUNT(*) as toplam_urun,
            SUM(CASE WHEN us.stok_adedi > 0 THEN 1 ELSE 0 END) as stokta_olan,
            SUM(CASE WHEN us.stok_adedi = 0 OR us.stok_adedi IS NULL THEN 1 ELSE 0 END) as stokta_olmayan,
            SUM(COALESCE(us.stok_adedi, 0)) as toplam_stok_adedi
        FROM urun u
        LEFT JOIN urun_stok us ON u.id = us.urun_id AND us.depo_id = ?
    ''', (secili_depo_id,)).fetchone()
    
    conn.close()
    
    return render_template('stok_listesi.html', 
                         stoklar=stoklar, 
                         depolar=depolar, 
                         secili_depo_id=int(secili_depo_id),
                         secili_depo=secili_depo,
                         toplam_stoklar=toplam_stoklar,
                         depo_istatistik=depo_istatistik)

# Ürün arama (AJAX)
@app.route('/api/urun_ara')
@login_required
def urun_ara():
    arama_terimi = request.args.get('q', '')
    depo_id = request.args.get('depo_id')
    
    if len(arama_terimi) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    
    if depo_id:
        # Depoya göre stok bilgisi ile birlikte ara
        urunler = conn.execute('''
            SELECT u.id, u.urun_adi, u.barkod, u.jant_ebati, COALESCE(u.desi, 0.00) as desi,
                   COALESCE(us.stok_adedi, 0) as stok_adedi
            FROM urun u
            LEFT JOIN urun_stok us ON u.id = us.urun_id AND us.depo_id = ?
            WHERE (u.urun_adi LIKE ? OR u.barkod LIKE ?)
            ORDER BY u.urun_adi
            LIMIT 10
        ''', (depo_id, f'%{arama_terimi}%', f'%{arama_terimi}%')).fetchall()
    else:
        # Sadece ürün bilgilerini ara
        urunler = conn.execute('''
            SELECT id, urun_adi, barkod, jant_ebati, COALESCE(desi, 0.00) as desi, 0 as stok_adedi
            FROM urun 
            WHERE urun_adi LIKE ? OR barkod LIKE ?
            ORDER BY urun_adi
            LIMIT 10
        ''', (f'%{arama_terimi}%', f'%{arama_terimi}%')).fetchall()
    
    conn.close()
    
    return jsonify([dict(urun) for urun in urunler])

# Ürün stok durumu (AJAX)
@app.route('/api/urun_stok_durumu/<int:urun_id>')
@login_required
def urun_stok_durumu(urun_id):
    conn = get_db_connection()
    
    stoklar = conn.execute('''
        SELECT 
            d.depo_adi,
            COALESCE(us.stok_adedi, 0) as stok_adedi
        FROM depo d
        LEFT JOIN urun_stok us ON d.id = us.depo_id AND us.urun_id = ?
        WHERE d.aktif = 1
        ORDER BY d.depo_adi
    ''', (urun_id,)).fetchall()
    
    conn.close()
    
    return jsonify([dict(stok) for stok in stoklar])

# Stok çıkışı - Yeni Fiş Sistemi
@app.route('/stok_cikisi', methods=['GET', 'POST'])
@login_required
def stok_cikisi():
    if request.method == 'POST':
        # Sepet verilerini al
        sepet_data = request.get_json()
        
        if not sepet_data or not sepet_data.get('items'):
            return jsonify({'success': False, 'message': 'Sepet boş!'})
        
        depo_id = sepet_data.get('depo_id')
        aciklama = sepet_data.get('aciklama', '')
        items = sepet_data.get('items', [])
        
        conn = get_db_connection()
        
        try:
            # Fiş numarası oluştur
            fis_no = f"FIS{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Stok kontrolü
            for item in items:
                urun_id = item['urun_id']
                cikis_adedi = int(item['adet'])
                
                mevcut_stok = conn.execute(
                    'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
                    (urun_id, depo_id)
                ).fetchone()
                
                if not mevcut_stok or mevcut_stok['stok_adedi'] < cikis_adedi:
                    urun_info = conn.execute('SELECT urun_adi FROM urun WHERE id = ?', (urun_id,)).fetchone()
                    return jsonify({
                        'success': False, 
                        'message': f"'{urun_info['urun_adi']}' için yetersiz stok! Mevcut: {mevcut_stok['stok_adedi'] if mevcut_stok else 0}, İstenen: {cikis_adedi}"
                    })
            
            # Fiş oluştur
            cursor = conn.execute('''
                INSERT INTO stok_cikis_fis 
                (fis_no, depo_id, aciklama, toplam_urun_adedi, toplam_adet, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fis_no, depo_id, aciklama, len(items), 
                  sum(int(item['adet']) for item in items),
                  session['kullanici_id'], session['kullanici_adi']))
            
            fis_id = cursor.lastrowid
            
            # Her ürün için işlem yap
            for item in items:
                urun_id = item['urun_id']
                cikis_adedi = int(item['adet'])
                
                # Ürün bilgilerini al
                urun = conn.execute('SELECT urun_adi, COALESCE(desi, 0.00) as desi FROM urun WHERE id = ?', (urun_id,)).fetchone()
                
                # Stok güncelle
                mevcut_stok = conn.execute(
                    'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
                    (urun_id, depo_id)
                ).fetchone()
                
                yeni_stok = mevcut_stok['stok_adedi'] - cikis_adedi
                conn.execute(
                    'UPDATE urun_stok SET stok_adedi = ?, updated_at = ? WHERE urun_id = ? AND depo_id = ?',
                    (yeni_stok, datetime.now(), urun_id, depo_id)
                )
                
                # Fiş detayına ekle
                birim_desi = urun['desi'] or 0
                toplam_desi = birim_desi * cikis_adedi
                
                conn.execute('''
                    INSERT INTO stok_cikis_fis_detay 
                    (fis_id, urun_id, urun_adi, cikis_adedi, birim_desi, toplam_desi, kargo_firmasi_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (fis_id, urun_id, urun['urun_adi'], cikis_adedi, birim_desi, toplam_desi, item.get('kargo_firmasi_id')))
                
                # İşlem geçmişine kaydet
                conn.execute('''
                    INSERT INTO islem_gecmisi 
                    (islem_tipi, urun_id, depo_id, urun_bilgisi, eski_deger, yeni_deger, 
                     tarih, kullanici_id, kullanici_adi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('STOK_CIKIS_FIS', urun_id, depo_id, 
                      f"Fiş: {fis_no} - {urun['urun_adi']} - {aciklama}",
                      str(mevcut_stok['stok_adedi']), str(yeni_stok),
                      datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': f'Fiş {fis_no} başarıyla oluşturuldu!',
                'fis_no': fis_no,
                'fis_id': fis_id
            })
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': f'Hata: {str(e)}'})
    
    # GET isteği - form göster
    conn = get_db_connection()
    depolar = conn.execute('SELECT * FROM depo WHERE aktif = 1').fetchall()
    conn.close()
    
    return render_template('stok_cikisi.html', depolar=depolar)

# Fiş listesi
@app.route('/fisler')
@app.route('/fis_listesi')  # Ek route ekleyelim
@login_required 
def fis_listesi():
    conn = get_db_connection()
    
    try:
        # Önce tabloların varlığını kontrol et
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stok_cikis_fis'")
        if not cursor.fetchone():
            # Tablo yoksa oluştur
            conn.execute('''
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
            conn.commit()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stok_cikis_fis_detay'")
        if not cursor.fetchone():
            # Detay tablosu yoksa oluştur
            conn.execute('''
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
            conn.commit()
        
        fisler = conn.execute('''
            SELECT 
                f.*,
                d.depo_adi,
                COUNT(fd.id) as urun_cesit_sayisi,
                SUM(fd.toplam_desi) as toplam_desi
            FROM stok_cikis_fis f
            LEFT JOIN depo d ON f.depo_id = d.id
            LEFT JOIN stok_cikis_fis_detay fd ON f.id = fd.fis_id
            GROUP BY f.id
            ORDER BY f.tarih DESC
            LIMIT 100
        ''').fetchall()
        
    except Exception as e:
        flash(f'Fiş listesi yüklenirken hata: {str(e)}', 'error')
        fisler = []
    finally:
        conn.close()
    
    return render_template('fis_listesi.html', fisler=fisler)

# Fiş detayı
@app.route('/fis/<int:fis_id>')
@login_required
def fis_detay(fis_id):
    conn = get_db_connection()
    
    # Fiş bilgisi
    fis = conn.execute('''
        SELECT f.*, d.depo_adi
        FROM stok_cikis_fis f
        LEFT JOIN depo d ON f.depo_id = d.id
        WHERE f.id = ?
    ''', (fis_id,)).fetchone()
    
    if not fis:
        flash('Fiş bulunamadı!', 'error')
        return redirect(url_for('fis_listesi'))
    
    # Fiş detayları
    detaylar = conn.execute('''
        SELECT fd.*, kf.firma_adi as kargo_firma_adi, kf.kisa_adi as kargo_kisa_adi
        FROM stok_cikis_fis_detay fd
        LEFT JOIN kargo_firmasi kf ON fd.kargo_firmasi_id = kf.id
        WHERE fd.fis_id = ?
        ORDER BY fd.urun_adi
    ''', (fis_id,)).fetchall()
    
    conn.close()
    
    return render_template('fis_detay.html', fis=fis, detaylar=detaylar)

# İşlem geçmişi
@app.route('/gecmis')
@login_required
def islem_gecmisi():
    conn = get_db_connection()
    
    gecmis = conn.execute('''
        SELECT 
            ig.*,
            d.depo_adi
        FROM islem_gecmisi ig
        LEFT JOIN depo d ON ig.depo_id = d.id
        ORDER BY ig.tarih DESC
        LIMIT 100
    ''').fetchall()
    
    conn.close()
    
    return render_template('islem_gecmisi.html', gecmis=gecmis)

# Depo transfer
@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def depo_transfer():
    if request.method == 'POST':
        urun_id = request.form['urun_id']
        kaynak_depo_id = request.form['kaynak_depo_id']
        hedef_depo_id = request.form['hedef_depo_id']
        transfer_adedi = int(request.form['transfer_adedi'])
        aciklama = request.form.get('aciklama', '')
        
        if kaynak_depo_id == hedef_depo_id:
            flash('Kaynak ve hedef depo aynı olamaz!', 'error')
            return redirect(url_for('depo_transfer'))
        
        conn = get_db_connection()
        
        # Kaynak depodaki stok kontrolü
        kaynak_stok = conn.execute(
            'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
            (urun_id, kaynak_depo_id)
        ).fetchone()
        
        if not kaynak_stok or kaynak_stok['stok_adedi'] < transfer_adedi:
            flash('Kaynak depoda yetersiz stok!', 'error')
        else:
            # Kaynak depodan düş
            yeni_kaynak_stok = kaynak_stok['stok_adedi'] - transfer_adedi
            conn.execute(
                'UPDATE urun_stok SET stok_adedi = ?, updated_at = ? WHERE urun_id = ? AND depo_id = ?',
                (yeni_kaynak_stok, datetime.now(), urun_id, kaynak_depo_id)
            )
            
            # Hedef depoya ekle
            hedef_stok = conn.execute(
                'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
                (urun_id, hedef_depo_id)
            ).fetchone()
            
            if hedef_stok:
                yeni_hedef_stok = hedef_stok['stok_adedi'] + transfer_adedi
                conn.execute(
                    'UPDATE urun_stok SET stok_adedi = ?, updated_at = ? WHERE urun_id = ? AND depo_id = ?',
                    (yeni_hedef_stok, datetime.now(), urun_id, hedef_depo_id)
                )
            else:
                conn.execute(
                    'INSERT INTO urun_stok (urun_id, depo_id, stok_adedi, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                    (urun_id, hedef_depo_id, transfer_adedi, datetime.now(), datetime.now())
                )
                yeni_hedef_stok = transfer_adedi
            
            # İşlem geçmişine kaydet
            urun_bilgisi = conn.execute('SELECT urun_adi FROM urun WHERE id = ?', (urun_id,)).fetchone()
            kaynak_depo = conn.execute('SELECT depo_adi FROM depo WHERE id = ?', (kaynak_depo_id,)).fetchone()
            hedef_depo = conn.execute('SELECT depo_adi FROM depo WHERE id = ?', (hedef_depo_id,)).fetchone()
            
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_id, depo_id, hedef_depo_id, urun_bilgisi, eski_deger, yeni_deger, 
                 tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('TRANSFER', urun_id, kaynak_depo_id, hedef_depo_id,
                  f"{urun_bilgisi['urun_adi']} - {kaynak_depo['depo_adi']} → {hedef_depo['depo_adi']} - {aciklama}",
                  f"{kaynak_stok['stok_adedi']} → {hedef_stok['stok_adedi'] if hedef_stok else 0}",
                  f"{yeni_kaynak_stok} → {yeni_hedef_stok}",
                  datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            flash(f'{transfer_adedi} adet transfer işlemi başarıyla tamamlandı!', 'success')
        
        conn.close()
        return redirect(url_for('depo_transfer'))
    
    # GET isteği - form göster
    conn = get_db_connection()
    depolar = conn.execute('SELECT * FROM depo WHERE aktif = 1').fetchall()
    conn.close()
    
    return render_template('depo_transfer.html', depolar=depolar)

# Stok girişi
@app.route('/stok_girisi', methods=['GET', 'POST'])
@login_required
def stok_girisi():
    if request.method == 'POST':
        urun_id = request.form['urun_id']
        depo_id = request.form['depo_id']
        giris_adedi = int(request.form['giris_adedi'])
        aciklama = request.form.get('aciklama', '')
        
        conn = get_db_connection()
        
        # Mevcut stok kontrolü
        mevcut_stok = conn.execute(
            'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
            (urun_id, depo_id)
        ).fetchone()
        
        if mevcut_stok:
            # Var olan stoku güncelle
            yeni_stok = mevcut_stok['stok_adedi'] + giris_adedi
            conn.execute(
                'UPDATE urun_stok SET stok_adedi = ?, updated_at = ? WHERE urun_id = ? AND depo_id = ?',
                (yeni_stok, datetime.now(), urun_id, depo_id)
            )
            eski_deger = mevcut_stok['stok_adedi']
        else:
            # Yeni stok kaydı oluştur
            conn.execute(
                'INSERT INTO urun_stok (urun_id, depo_id, stok_adedi, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (urun_id, depo_id, giris_adedi, datetime.now(), datetime.now())
            )
            yeni_stok = giris_adedi
            eski_deger = 0
        
        # İşlem geçmişine kaydet
        urun_bilgisi = conn.execute('SELECT urun_adi FROM urun WHERE id = ?', (urun_id,)).fetchone()
        conn.execute('''
            INSERT INTO islem_gecmisi 
            (islem_tipi, urun_id, depo_id, urun_bilgisi, eski_deger, yeni_deger, 
             tarih, kullanici_id, kullanici_adi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('STOK_GIRIS', urun_id, depo_id, 
              f"{urun_bilgisi['urun_adi']} - {aciklama}",
              str(eski_deger), str(yeni_stok),
              datetime.now(), session['kullanici_id'], session['kullanici_adi']))
        
        conn.commit()
        flash(f'{giris_adedi} adet stok girişi başarıyla kaydedildi!', 'success')
        
        conn.close()
        return redirect(url_for('stok_girisi'))
    
    # GET isteği - form göster
    conn = get_db_connection()
    depolar = conn.execute('SELECT * FROM depo WHERE aktif = 1').fetchall()
    conn.close()
    
    return render_template('stok_girisi.html', depolar=depolar)

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Ürün yönetimi
@app.route('/urunler')
@login_required
def urun_listesi():
    conn = get_db_connection()
    
    # Arama parametresi
    arama = request.args.get('arama', '')
    
    if arama:
        urunler = conn.execute('''
            SELECT * FROM urun 
            WHERE urun_adi LIKE ? OR barkod LIKE ? OR jant_ebati LIKE ?
            ORDER BY urun_adi
        ''', (f'%{arama}%', f'%{arama}%', f'%{arama}%')).fetchall()
    else:
        urunler = conn.execute('SELECT * FROM urun ORDER BY urun_adi').fetchall()
    
    conn.close()
    
    return render_template('urun_listesi.html', urunler=urunler, arama=arama)

# Ürün ekleme
@app.route('/urun_ekle', methods=['GET', 'POST'])
@login_required
def urun_ekle():
    if request.method == 'POST':
        urun_adi = request.form['urun_adi'].strip()
        jant_ebati = request.form['jant_ebati'].strip()
        desi = float(request.form.get('desi', 0.00) or 0.00)
        barkod = request.form['barkod'].strip() if request.form['barkod'].strip() else '00'
        aciklama = request.form.get('aciklama', '').strip()
        
        if not urun_adi or not jant_ebati:
            flash('Ürün adı ve jant ebatı zorunludur!', 'error')
            return redirect(url_for('urun_ekle'))
        
        conn = get_db_connection()
        
        # Barkod benzersizlik kontrolü (sadece "00" değilse)
        if barkod and barkod != '00':
            existing_barcode = conn.execute('SELECT id FROM urun WHERE barkod = ?', (barkod,)).fetchone()
            if existing_barcode:
                flash('Bu barkod zaten kullanılıyor!', 'error')
                conn.close()
                return redirect(url_for('urun_ekle'))
        
        try:
            cursor = conn.execute('''
                INSERT INTO urun (urun_adi, jant_ebati, desi, barkod, aciklama, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (urun_adi, jant_ebati, desi, barkod, aciklama or None, datetime.now(), datetime.now()))
            
            urun_id = cursor.lastrowid
            
            # İşlem geçmişine kaydet
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_id, urun_bilgisi, yeni_deger, tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('URUN_EKLEME', urun_id, f"Yeni ürün: {urun_adi}", 
                  f"Jant: {jant_ebati}, Desi: {desi} kg, Barkod: {barkod}", 
                  datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            flash(f'Ürün "{urun_adi}" başarıyla eklendi!', 'success')
            
        except Exception as e:
            flash(f'Ürün eklenirken hata oluştu: {str(e)}', 'error')
        finally:
            conn.close()
            
        return redirect(url_for('urun_listesi'))
    
    return render_template('urun_ekle.html')

# Ürün güncelleme
@app.route('/urun_guncelle/<int:urun_id>', methods=['GET', 'POST'])
@login_required
def urun_guncelle(urun_id):
    conn = get_db_connection()
    
    # Ürün bilgilerini al
    urun = conn.execute('SELECT * FROM urun WHERE id = ?', (urun_id,)).fetchone()
    if not urun:
        flash('Ürün bulunamadı!', 'error')
        conn.close()
        return redirect(url_for('urun_listesi'))
    
    if request.method == 'POST':
        urun_adi = request.form['urun_adi'].strip()
        jant_ebati = request.form['jant_ebati'].strip()
        desi = float(request.form.get('desi', 0.00) or 0.00)
        barkod = request.form['barkod'].strip() if request.form['barkod'].strip() else '00'
        aciklama = request.form.get('aciklama', '').strip()
        
        if not urun_adi or not jant_ebati:
            flash('Ürün adı ve jant ebatı zorunludur!', 'error')
            return redirect(url_for('urun_guncelle', urun_id=urun_id))
        
        # Barkod benzersizlik kontrolü (kendisi hariç ve sadece "00" değilse)
        if barkod and barkod != '00':
            existing_barcode = conn.execute(
                'SELECT id FROM urun WHERE barkod = ? AND id != ?', 
                (barkod, urun_id)
            ).fetchone()
            if existing_barcode:
                flash('Bu barkod başka bir ürün tarafından kullanılıyor!', 'error')
                conn.close()
                return redirect(url_for('urun_guncelle', urun_id=urun_id))
        
        try:
            # Eski değerleri kaydet
            eski_degerler = f"Ad: {urun['urun_adi']}, Jant: {urun['jant_ebati']}, Desi: {urun.get('desi', 0)} kg, Barkod: {urun['barkod'] or '00'}"
            yeni_degerler = f"Ad: {urun_adi}, Jant: {jant_ebati}, Desi: {desi} kg, Barkod: {barkod}"
            
            # Güncelleme
            conn.execute('''
                UPDATE urun 
                SET urun_adi = ?, jant_ebati = ?, desi = ?, barkod = ?, aciklama = ?, updated_at = ?
                WHERE id = ?
            ''', (urun_adi, jant_ebati, desi, barkod, aciklama or None, datetime.now(), urun_id))
            
            # İşlem geçmişine kaydet
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_id, urun_bilgisi, eski_deger, yeni_deger, tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('URUN_GUNCELLEME', urun_id, f"Ürün güncellendi: {urun_adi}", 
                  eski_degerler, yeni_degerler,
                  datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            flash(f'Ürün "{urun_adi}" başarıyla güncellendi!', 'success')
            
        except Exception as e:
            flash(f'Ürün güncellenirken hata oluştu: {str(e)}', 'error')
        finally:
            conn.close()
            
        return redirect(url_for('urun_listesi'))
    
    conn.close()
    return render_template('urun_guncelle.html', urun=urun)

# Ürün silme
@app.route('/urun_sil/<int:urun_id>', methods=['POST'])
@login_required
def urun_sil(urun_id):
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('urun_listesi'))
    
    conn = get_db_connection()
    
    # Ürün bilgilerini al
    urun = conn.execute('SELECT * FROM urun WHERE id = ?', (urun_id,)).fetchone()
    if not urun:
        flash('Ürün bulunamadı!', 'error')
        conn.close()
        return redirect(url_for('urun_listesi'))
    
    # Stok kontrolü
    stok_var = conn.execute('SELECT COUNT(*) as sayac FROM urun_stok WHERE urun_id = ? AND stok_adedi > 0', (urun_id,)).fetchone()
    if stok_var['sayac'] > 0:
        flash('Bu ürünün stokta kaydı bulunuyor! Önce stokları sıfırlamanız gerekir.', 'error')
        conn.close()
        return redirect(url_for('urun_listesi'))
    
    try:
        # Stok kayıtlarını sil
        conn.execute('DELETE FROM urun_stok WHERE urun_id = ?', (urun_id,))
        
        # Ürünü sil
        conn.execute('DELETE FROM urun WHERE id = ?', (urun_id,))
        
        # İşlem geçmişine kaydet
        conn.execute('''
            INSERT INTO islem_gecmisi 
            (islem_tipi, urun_bilgisi, eski_deger, tarih, kullanici_id, kullanici_adi)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('URUN_SILME', f"Silinen ürün: {urun['urun_adi']}", 
              f"ID: {urun_id}, Barkod: {urun['barkod'] or 'N/A'}", 
              datetime.now(), session['kullanici_id'], session['kullanici_adi']))
        
        conn.commit()
        flash(f'Ürün "{urun["urun_adi"]}" başarıyla silindi!', 'success')
        
    except Exception as e:
        flash(f'Ürün silinirken hata oluştu: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('urun_listesi'))

# Kullanıcı listesi (Sadece admin)
@app.route('/kullanici_listesi')
@login_required
def kullanici_listesi():
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    kullanicilar = conn.execute('''
        SELECT id, kullanici_adi, tam_ad, rol, aktif, created_at, last_login
        FROM kullanici ORDER BY kullanici_adi
    ''').fetchall()
    conn.close()
    
    return render_template('kullanici_listesi.html', kullanicilar=kullanicilar)

# Kullanıcı şifre sıfırlama (Sadece admin)
@app.route('/kullanici_sifre_sifirla/<int:kullanici_id>', methods=['POST'])
@login_required
def kullanici_sifre_sifirla(kullanici_id):
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('index'))
    
    # Kendi şifresini sıfırlayamaz
    if kullanici_id == session['kullanici_id']:
        flash('Kendi şifrenizi bu şekilde sıfırlayamazsınız!', 'error')
        return redirect(url_for('kullanici_listesi'))
    
    conn = get_db_connection()
    
    # Kullanıcı kontrolü
    kullanici = conn.execute('SELECT * FROM kullanici WHERE id = ?', (kullanici_id,)).fetchone()
    if not kullanici:
        flash('Kullanıcı bulunamadı!', 'error')
        conn.close()
        return redirect(url_for('kullanici_listesi'))
    
    try:
        # Varsayılan şifre: kullanici_adi + 123
        yeni_sifre = kullanici['kullanici_adi'] + '123'
        yeni_sifre_hash = hashlib.sha256(yeni_sifre.encode()).hexdigest()
        
        # Şifre güncelleme
        conn.execute(
            'UPDATE kullanici SET sifre_hash = ?, updated_at = ? WHERE id = ?',
            (yeni_sifre_hash, datetime.now(), kullanici_id)
        )
        
        # İşlem geçmişine kaydet
        conn.execute('''
            INSERT INTO islem_gecmisi 
            (islem_tipi, urun_bilgisi, tarih, kullanici_id, kullanici_adi)
            VALUES (?, ?, ?, ?, ?)
        ''', ('SIFRE_SIFIRLAMA', f"Admin tarafından şifre sıfırlandı: {kullanici['kullanici_adi']}", 
              datetime.now(), session['kullanici_id'], session['kullanici_adi']))
        
        conn.commit()
        flash(f'{kullanici["kullanici_adi"]} kullanıcısının şifresi sıfırlandı! Yeni şifre: {yeni_sifre}', 'success')
        
    except Exception as e:
        flash(f'Şifre sıfırlanırken hata oluştu: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('kullanici_listesi'))

# Günlük Rapor
@app.route('/gunluk_rapor')
@login_required
def gunluk_rapor():
    """Günlük giriş ve çıkış raporunu gösterir"""
    
    # Tarih filtresi (varsayılan: bugün)
    secili_tarih = request.args.get('tarih', datetime.now().strftime('%Y-%m-%d'))
    baslangic_tarih = request.args.get('baslangic_tarih', secili_tarih)
    bitis_tarih = request.args.get('bitis_tarih', secili_tarih)
    
    conn = get_db_connection()
    
    # Giriş işlemleri (STOK_GIRISI işlemlerini al)
    giris_islemleri = conn.execute('''
        SELECT ig.*, u.urun_adi, u.jant_ebati, u.barkod, d.depo_adi
        FROM islem_gecmisi ig
        LEFT JOIN urun u ON ig.urun_id = u.id
        LEFT JOIN depo d ON ig.depo_id = d.id
        WHERE ig.islem_tipi = 'STOK_GIRISI' 
        AND DATE(ig.tarih) = ?
        ORDER BY ig.tarih DESC
    ''', (secili_tarih,)).fetchall()
    
    # Çıkış işlemleri (STOK_CIKISI işlemlerini al)
    cikis_islemleri = conn.execute('''
        SELECT ig.*, u.urun_adi, u.jant_ebati, u.barkod, d.depo_adi
        FROM islem_gecmisi ig
        LEFT JOIN urun u ON ig.urun_id = u.id
        LEFT JOIN depo d ON ig.depo_id = d.id
        WHERE ig.islem_tipi = 'STOK_CIKISI' 
        AND DATE(ig.tarih) = ?
        ORDER BY ig.tarih DESC
    ''', (secili_tarih,)).fetchall()
    
    # Transfer işlemleri (DEPO_TRANSFER işlemlerini al)
    transfer_islemleri = conn.execute('''
        SELECT ig.*, u.urun_adi, u.jant_ebati, u.barkod, d.depo_adi,
               d2.depo_adi as hedef_depo_adi
        FROM islem_gecmisi ig
        LEFT JOIN urun u ON ig.urun_id = u.id
        LEFT JOIN depo d ON ig.depo_id = d.id
        LEFT JOIN depo d2 ON ig.hedef_depo_id = d2.id
        WHERE ig.islem_tipi = 'DEPO_TRANSFER' 
        AND DATE(ig.tarih) = ?
        ORDER BY ig.tarih DESC
    ''', (secili_tarih,)).fetchall()
    
    # Günlük özet
    ozet = conn.execute('''
        SELECT 
            islem_tipi,
            COUNT(*) as islem_sayisi
        FROM islem_gecmisi 
        WHERE DATE(tarih) = ?
        AND islem_tipi IN ('STOK_GIRISI', 'STOK_CIKISI', 'DEPO_TRANSFER')
        GROUP BY islem_tipi
    ''', (secili_tarih,)).fetchall()
    
    # Kargo firmalarına göre günlük çıkış raporu (tabloların varlığını kontrol et)
    kargo_raporu = []
    try:
        kargo_raporu = conn.execute('''
            SELECT 
                COALESCE(kf.firma_adi, 'Kargo Belirtilmemiş') as kargo_firma,
                COUNT(DISTINCT fd.fis_id) as fis_sayisi,
                COUNT(fd.id) as urun_cesit_sayisi,
                SUM(fd.cikis_adedi) as toplam_adet,
                ROUND(COALESCE(SUM(fd.toplam_desi), 0), 2) as toplam_desi
            FROM stok_cikis_fis_detay fd
            LEFT JOIN stok_cikis_fis f ON fd.fis_id = f.id
            LEFT JOIN kargo_firmasi kf ON fd.kargo_firmasi_id = kf.id
            WHERE DATE(f.tarih) BETWEEN ? AND ?
            GROUP BY kf.firma_adi
            ORDER BY toplam_adet DESC
        ''', (baslangic_tarih, bitis_tarih)).fetchall()
    except Exception as e:
        print(f"Kargo raporu hatası: {e}")
    
    # Günlük fiş özeti
    fis_ozeti = {}
    try:
        fis_ozeti_data = conn.execute('''
            SELECT 
                COUNT(DISTINCT f.id) as toplam_fis,
                COUNT(fd.id) as toplam_urun_cesit,
                SUM(fd.cikis_adedi) as toplam_cikis_adet,
                ROUND(COALESCE(SUM(fd.toplam_desi), 0), 2) as toplam_desi
            FROM stok_cikis_fis f
            LEFT JOIN stok_cikis_fis_detay fd ON f.id = fd.fis_id
            WHERE DATE(f.tarih) BETWEEN ? AND ?
        ''', (baslangic_tarih, bitis_tarih)).fetchone()
        
        if fis_ozeti_data:
            fis_ozeti = dict(fis_ozeti_data)
    except Exception as e:
        print(f"Fiş özeti hatası: {e}")
    
    conn.close()
    
    # Özet verilerini dictionary'e çevir
    ozet_dict = {}
    for o in ozet:
        # Miktarları yeni_deger'den çıkarabilir ya da standart 1 verebiliriz
        ozet_dict[o['islem_tipi']] = {
            'islem_sayisi': o['islem_sayisi'],
            'toplam_miktar': o['islem_sayisi']  # Şimdilik işlem sayısını miktar olarak gösterelim
        }
    
    return render_template('gunluk_rapor.html', 
                         giris_islemleri=giris_islemleri,
                         cikis_islemleri=cikis_islemleri,
                         transfer_islemleri=transfer_islemleri,
                         ozet=ozet_dict,
                         kargo_raporu=kargo_raporu,
                         fis_ozeti=fis_ozeti,
                         secili_tarih=secili_tarih,
                         baslangic_tarih=baslangic_tarih,
                         bitis_tarih=bitis_tarih)

# Kargo Firmalarını Listele API
@app.route('/api/kargo_firmalari')
@login_required
def api_kargo_firmalari():
    """Aktif kargo firmalarını listeler"""
    try:
        conn = get_db_connection()
        kargo_firmalari = conn.execute('''
            SELECT id, firma_adi, kisa_adi, telefon, website 
            FROM kargo_firmasi 
            WHERE aktif = 1 
            ORDER BY firma_adi
        ''').fetchall()
        
        # Varsayılan kargo firmasını al
        varsayilan_kargo = None
        try:
            varsayilan = conn.execute('SELECT deger FROM ayarlar WHERE anahtar = ?', ('varsayilan_kargo_firmasi_id',)).fetchone()
            if varsayilan:
                varsayilan_kargo = int(varsayilan['deger'])
        except:
            pass
        
        conn.close()
        
        return jsonify({
            'firmalar': [{
                'id': firma['id'],
                'firma_adi': firma['firma_adi'],
                'kisa_adi': firma['kisa_adi'],
                'telefon': firma['telefon'],
                'website': firma['website']
            } for firma in kargo_firmalari],
            'varsayilan_id': varsayilan_kargo
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Database Fix - Geçici route
# Sistem Ayarları
@app.route('/ayarlar')
@login_required
def ayarlar():
    """Sistem ayarları sayfası"""
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Kargo firmalarını al
    kargo_firmalari = conn.execute('''
        SELECT * FROM kargo_firmasi 
        ORDER BY firma_adi
    ''').fetchall()
    
    # Ayarları al
    ayarlar = {}
    try:
        ayarlar_rows = conn.execute('SELECT anahtar, deger FROM ayarlar').fetchall()
        for row in ayarlar_rows:
            ayarlar[row['anahtar']] = row['deger']
    except:
        # Ayarlar tablosu yoksa oluştur
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ayarlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anahtar VARCHAR(100) NOT NULL UNIQUE,
                deger TEXT,
                aciklama TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    
    conn.close()
    
    return render_template('ayarlar.html', 
                         kargo_firmalari=kargo_firmalari,
                         ayarlar=ayarlar)

# Ayar Kaydet
@app.route('/ayar_kaydet', methods=['POST'])
@login_required
def ayar_kaydet():
    """Ayar kaydet"""
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('index'))
    
    anahtar = request.form.get('anahtar')
    deger = request.form.get('deger')
    aciklama = request.form.get('aciklama', '')
    
    if not anahtar:
        flash('Ayar anahtarı gereklidir!', 'error')
        return redirect(url_for('ayarlar'))
    
    conn = get_db_connection()
    
    try:
        # Ayar var mı kontrol et
        mevcut = conn.execute('SELECT id FROM ayarlar WHERE anahtar = ?', (anahtar,)).fetchone()
        
        if mevcut:
            # Güncelle
            conn.execute('''
                UPDATE ayarlar 
                SET deger = ?, aciklama = ?, updated_at = ?
                WHERE anahtar = ?
            ''', (deger, aciklama, datetime.now(), anahtar))
        else:
            # Yeni ekle
            conn.execute('''
                INSERT INTO ayarlar (anahtar, deger, aciklama, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (anahtar, deger, aciklama, datetime.now(), datetime.now()))
        
        conn.commit()
        flash('Ayar başarıyla kaydedildi!', 'success')
        
    except Exception as e:
        flash(f'Ayar kaydedilirken hata oluştu: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('ayarlar'))

# Kargo Firması Ekle/Güncelle
@app.route('/kargo_firma_kaydet', methods=['POST'])
@login_required
def kargo_firma_kaydet():
    """Kargo firması ekle veya güncelle"""
    if session.get('rol') != 'admin':
        flash('Bu işlem için admin yetkisi gereklidir!', 'error')
        return redirect(url_for('index'))
    
    firma_id = request.form.get('firma_id')
    firma_adi = request.form.get('firma_adi', '').strip()
    kisa_adi = request.form.get('kisa_adi', '').strip()
    telefon = request.form.get('telefon', '').strip()
    website = request.form.get('website', '').strip()
    aktif = request.form.get('aktif') == '1'
    
    if not firma_adi:
        flash('Firma adı gereklidir!', 'error')
        return redirect(url_for('ayarlar'))
    
    conn = get_db_connection()
    
    try:
        if firma_id:  # Güncelle
            conn.execute('''
                UPDATE kargo_firmasi 
                SET firma_adi = ?, kisa_adi = ?, telefon = ?, website = ?, aktif = ?
                WHERE id = ?
            ''', (firma_adi, kisa_adi, telefon, website, aktif, firma_id))
            flash('Kargo firması başarıyla güncellendi!', 'success')
        else:  # Yeni ekle
            conn.execute('''
                INSERT INTO kargo_firmasi (firma_adi, kisa_adi, telefon, website, aktif)
                VALUES (?, ?, ?, ?, ?)
            ''', (firma_adi, kisa_adi, telefon, website, aktif))
            flash('Kargo firması başarıyla eklendi!', 'success')
        
        conn.commit()
        
    except Exception as e:
        flash(f'Kargo firması kaydedilirken hata oluştu: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('ayarlar'))


# Application entry point
if __name__ == '__main__':
    # Configuration from environment variables
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'  # Production için False
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"🚀 BikeStock uygulaması başlatılıyor...")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🐛 Debug: {debug}")
    print("=" * 50)
    
    app.run(debug=debug, host=host, port=port)