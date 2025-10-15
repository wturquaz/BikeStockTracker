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
    
    if len(arama_terimi) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    
    # Hem ürün adında hem barkodda ara
    urunler = conn.execute('''
        SELECT id, urun_adi, barkod, jant_ebati
        FROM urun 
        WHERE urun_adi LIKE ? OR barkod LIKE ?
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

# Stok çıkışı
@app.route('/stok_cikisi', methods=['GET', 'POST'])
@login_required
def stok_cikisi():
    if request.method == 'POST':
        urun_id = request.form['urun_id']
        depo_id = request.form['depo_id']
        cikis_adedi = int(request.form['cikis_adedi'])
        aciklama = request.form.get('aciklama', '')
        
        conn = get_db_connection()
        
        # Mevcut stok kontrolü
        mevcut_stok = conn.execute(
            'SELECT stok_adedi FROM urun_stok WHERE urun_id = ? AND depo_id = ?',
            (urun_id, depo_id)
        ).fetchone()
        
        if not mevcut_stok or mevcut_stok['stok_adedi'] < cikis_adedi:
            flash('Yetersiz stok!', 'error')
        else:
            # Stok güncelle
            yeni_stok = mevcut_stok['stok_adedi'] - cikis_adedi
            conn.execute(
                'UPDATE urun_stok SET stok_adedi = ?, updated_at = ? WHERE urun_id = ? AND depo_id = ?',
                (yeni_stok, datetime.now(), urun_id, depo_id)
            )
            
            # İşlem geçmişine kaydet
            urun_bilgisi = conn.execute('SELECT urun_adi FROM urun WHERE id = ?', (urun_id,)).fetchone()
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_id, depo_id, urun_bilgisi, eski_deger, yeni_deger, 
                 tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('STOK_CIKIS', urun_id, depo_id, 
                  f"{urun_bilgisi['urun_adi']} - {aciklama}",
                  str(mevcut_stok['stok_adedi']), str(yeni_stok),
                  datetime.now(), session['kullanici_id'], session['kullanici_adi']))
            
            conn.commit()
            flash(f'{cikis_adedi} adet stok çıkışı başarıyla kaydedildi!', 'success')
        
        conn.close()
        return redirect(url_for('stok_cikisi'))
    
    # GET isteği - form göster
    conn = get_db_connection()
    depolar = conn.execute('SELECT * FROM depo WHERE aktif = 1').fetchall()
    conn.close()
    
    return render_template('stok_cikisi.html', depolar=depolar)

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
        barkod = request.form['barkod'].strip()
        aciklama = request.form.get('aciklama', '').strip()
        
        if not urun_adi or not jant_ebati:
            flash('Ürün adı ve jant ebatı zorunludur!', 'error')
            return redirect(url_for('urun_ekle'))
        
        conn = get_db_connection()
        
        # Barkod benzersizlik kontrolü
        if barkod:
            existing_barcode = conn.execute('SELECT id FROM urun WHERE barkod = ?', (barkod,)).fetchone()
            if existing_barcode:
                flash('Bu barkod zaten kullanılıyor!', 'error')
                conn.close()
                return redirect(url_for('urun_ekle'))
        
        try:
            cursor = conn.execute('''
                INSERT INTO urun (urun_adi, jant_ebati, barkod, aciklama, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (urun_adi, jant_ebati, barkod or None, aciklama or None, datetime.now(), datetime.now()))
            
            urun_id = cursor.lastrowid
            
            # İşlem geçmişine kaydet
            conn.execute('''
                INSERT INTO islem_gecmisi 
                (islem_tipi, urun_id, urun_bilgisi, yeni_deger, tarih, kullanici_id, kullanici_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('URUN_EKLEME', urun_id, f"Yeni ürün: {urun_adi}", 
                  f"Jant: {jant_ebati}, Barkod: {barkod or 'N/A'}", 
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
        barkod = request.form['barkod'].strip()
        aciklama = request.form.get('aciklama', '').strip()
        
        if not urun_adi or not jant_ebati:
            flash('Ürün adı ve jant ebatı zorunludur!', 'error')
            return redirect(url_for('urun_guncelle', urun_id=urun_id))
        
        # Barkod benzersizlik kontrolü (kendisi hariç)
        if barkod:
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
            eski_degerler = f"Ad: {urun['urun_adi']}, Jant: {urun['jant_ebati']}, Barkod: {urun['barkod'] or 'N/A'}"
            yeni_degerler = f"Ad: {urun_adi}, Jant: {jant_ebati}, Barkod: {barkod or 'N/A'}"
            
            # Güncelleme
            conn.execute('''
                UPDATE urun 
                SET urun_adi = ?, jant_ebati = ?, barkod = ?, aciklama = ?, updated_at = ?
                WHERE id = ?
            ''', (urun_adi, jant_ebati, barkod or None, aciklama or None, datetime.now(), urun_id))
            
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
                         secili_tarih=secili_tarih)


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