# BikeStock - Bisiklet Stok Takip Sistemi

## 🚴‍♂️ Genel Bakış

BikeStock, depo bazlı bisiklet stok takip ve yönetim sistemi için geliştirilmiş modern bir web uygulamasıdır.

### ✨ Özellikler

- **Depo Bazlı Stok Yönetimi**: Birden fazla depo için ayrı stok takibi
- **Barkod Desteği**: Hem barkod hem ürün adı ile hızlı arama
- **Stok İşlemleri**: Giriş, çıkış ve depo arası transfer
- **Kullanıcı Yönetimi**: Güvenli giriş ve yetkilendirme sistemi
- **İşlem Geçmişi**: Tüm stok hareketlerinin detaylı kaydı
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu arayüz

### 🛠️ Teknoloji Stack

- **Backend**: Python Flask
- **Veritabanı**: SQLite
- **Frontend**: Bootstrap 5, jQuery
- **Güvenlik**: Session tabanlı kimlik doğrulama

## 🚀 Kurulum

### Gereksinimler

- Python 3.8+
- pip (Python paket yöneticisi)

### Lokal Kurulum

1. Projeyi klonlayın:
```bash
git clone <repo-url>
cd BikeStockTracker
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Veritabanını güncelleyin:
```bash
python safe_upgrade_database.py
```

4. Uygulamayı başlatın:
```bash
python app.py
```

5. Tarayıcınızda `http://localhost:5000` adresine gidin

### Varsayılan Giriş Bilgileri

- **Kullanıcı Adı**: admin
- **Şifre**: admin123

⚠️ **Güvenlik**: Üretim ortamında mutlaka şifreyi değiştirin!

## 📋 Kullanım

### Stok Listesi
- Depo bazlı stok durumunu görüntüleyin
- Stok seviyelerine göre renk kodlu gösterim
- Kritik stok uyarıları

### Stok Çıkışı
- Barkod veya ürün adı ile hızlı arama
- Stok yetersizlik kontrolü
- Detaylı açıklama ekleme

### Stok Girişi
- Yeni ürün girişi
- Mevcut stok güncelleme
- Tedarik takibi

### Depo Transfer
- Depolar arası stok aktarımı
- Kaynak/hedef depo kontrolleri
- Transfer geçmişi

### İşlem Geçmişi
- Tüm stok hareketlerinin kaydı
- Kullanıcı bazlı işlem takibi
- Tarih/saat damgası

## 🌐 Ücretsiz Deployment

Bu sistem aşağıdaki platformlarda ücretsiz olarak yayımlanabilir:

### 1. Render.com (Önerilen)
- SQLite veritabanı desteği
- Otomatik HTTPS
- Kolay deployment

### 2. Railway.app
- GitHub entegrasyonu
- Otomatik build
- Persistent storage

### 3. Heroku (Sınırlı)
- PostgreSQL gerektirir
- Dosya storage sınırları

Detaylı deployment talimatları için `DEPLOYMENT.md` dosyasına bakın.

## 🔧 Yapılandırma

### Güvenlik Ayarları

`app.py` dosyasında:
```python
app.secret_key = 'your-secret-key-change-this'  # Değiştirin!
```

### Veritabanı Bağlantısı

SQLite varsayılan olarak kullanılır. PostgreSQL için konfigürasyon değişikliği gereklidir.

## 📊 Veritabanı Şeması

### Ana Tablolar

- **kullanici**: Kullanıcı bilgileri ve yetkilendirme
- **depo**: Depo tanımları
- **urun**: Ürün bilgileri ve barkodlar
- **urun_stok**: Depo bazlı stok miktarları
- **islem_gecmisi**: Tüm stok işlemlerinin kaydı

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Branch'i push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🐛 Hata Bildirimi

Hataları GitHub Issues üzerinden bildirebilirsiniz.

## 📞 İletişim

Sorularınız için: [iletişim bilgisi]

---

**BikeStock** - Bisiklet stoklarınızı profesyonelce yönetin! 🚴‍♂️