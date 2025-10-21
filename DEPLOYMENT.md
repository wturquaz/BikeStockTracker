# 🚀 BikeStock Deployment Rehberi

Bu rehber, BikeStock uygulamanızı ücretsiz bulut platformlarında nasıl yayımlayacağınızı gösterir.

## 📋 Deployment Öncesi Hazırlık

### 1. Gerekli Dosyaları Oluşturun

Aşağıdaki dosyaların proje klasörünüzde olduğundan emin olun:

```
BikeStockTracker/
├── app.py
├── requirements.txt
├── stok_takip.db
├── upgrade_database.py
├── templates/
├── README.md
└── deployment dosyaları (aşağıda)
```

### 2. requirements.txt Güncelleyin

```txt
flask==2.3.3
flask-session==0.5.0
werkzeug==2.3.7
gunicorn==21.2.0
```

## 🎯 Platform Seçenekleri

### Option 1: Render.com (Önerilen) ⭐

**Avantajları:**

- SQLite desteği
- Otomatik HTTPS
- Kolay setup
- Persistent disk

**Deployment Adımları:**

1. **GitHub'a Upload Edin**

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/kullaniciadi/BikeStockTracker.git
   git push -u origin main
   ```
2. **Render Dosyaları Oluşturun**

   **`render.yaml`** (proje kök dizininde):

   ```yaml
   services:
     - type: web
       name: bikestock
       env: python
       buildCommand: "pip install -r requirements.txt"
       startCommand: "gunicorn app:app"
       envVars:
         - key: PYTHON_VERSION
           value: 3.11.0
   ```

   **`gunicorn_config.py`**:

   ```python
   bind = "0.0.0.0:10000"
   workers = 1
   timeout = 120
   ```
3. **app.py Güncelleyin** (production ayarları):

   ```python
   import os

   # ... existing code ...

   if __name__ == '__main__':
       port = int(os.environ.get('PORT', 5000))
       debug = os.environ.get('DEBUG', 'False').lower() == 'true'
       app.run(debug=debug, host='0.0.0.0', port=port)
   ```
4. **Render'da Deploy Edin**

   - render.com'a giriş yapın
   - "New +" → "Web Service"
   - GitHub repository'nizi bağlayın
   - Otomatik deploy başlar

### Option 2: Railway.app 🚂

**Avantajları:**

- GitHub entegrasyonu
- Otomatik build
- SQLite desteği

**Deployment Adımları:**

1. **railway.json Oluşturun**:

   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "nixpacks"
     },
     "deploy": {
       "startCommand": "gunicorn app:app"
     }
   }
   ```
2. **Railway'de Deploy**:

   - railway.app'e giriş yapın
   - "New Project" → "Deploy from GitHub repo"
   - Repository'nizi seçin
   - Otomatik deploy başlar

### Option 3: Fly.io ✈️

**Avantajları:**

- SQLite persistent volume
- Global deployment
- Docker desteği

**Deployment Adımları:**

1. **Dockerfile Oluşturun**:

   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   EXPOSE 8080

   CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
   ```
2. **fly.toml Oluşturun**:

   ```toml
   app = "bikestock-app"

   [build]

   [env]
     PORT = "8080"

   [[services]]
     http_checks = []
     internal_port = 8080
     processes = ["app"]
     protocol = "tcp"
     script_checks = []

     [[services.ports]]
       force_https = true
       handlers = ["http"]
       port = 80

     [[services.ports]]
       handlers = ["tls", "http"]
       port = 443

   [[mounts]]
     source = "bikestock_data"
     destination = "/app/data"
   ```
3. **Deploy Komutları**:

   ```bash
   flyctl auth login
   flyctl apps create bikestock-app
   flyctl volumes create bikestock_data --size 1
   flyctl deploy
   ```

## 🔧 Production Optimizasyonları

### 1. Güvenlik Ayarları

**app.py** güncellemesi:

```python
import os
import secrets

# Production secret key
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# HTTPS yönlendirmesi
@app.before_request
def force_https():
    if not request.is_secure and app.env != 'development':
        return redirect(request.url.replace('http://', 'https://'))
```

### 2. Environment Variables

Platform ayarlarında şu değişkenleri ekleyin:

```
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=sqlite:///./stok_takip.db  # veya PostgreSQL URL
```

### 3. Database Backup

**backup.py** oluşturun:

```python
import sqlite3
import os
from datetime import datetime

def backup_database():
    source = 'stok_takip.db'
    backup_name = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
  
    if os.path.exists(source):
        # SQLite backup
        conn = sqlite3.connect(source)
        backup = sqlite3.connect(backup_name)
        conn.backup(backup)
        backup.close()
        conn.close()
        print(f"Backup created: {backup_name}")

if __name__ == "__main__":
    backup_database()
```

## 🌐 Domain Bağlama

### Custom Domain Ayarları

1. **DNS Kayıtları**:

   ```
   Type: CNAME
   Name: www
   Value: your-app.render.com (veya platform URL'i)
   ```
2. **Platform Ayarları**:

   - Render: Settings → Custom Domains
   - Railway: Settings → Domains
   - Fly.io: `flyctl certs create yourdomain.com`

## 📊 Monitoring ve Logs

### Log Görüntüleme

```bash
# Render
render logs

# Railway
railway logs

# Fly.io
flyctl logs
```

### Health Check

**healthcheck.py**:

```python
from flask import jsonify

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })
```

## 🔄 Güncelleme İşlemi

### Git ile Güncelleme

```bash
git add .
git commit -m "Update features"
git push origin main
```

Platformlar otomatik olarak yeni versiyonu deploy eder.

### Database Migration

Veritabanı değişiklikleri için:

```python
# migration.py
def migrate_database():
    conn = sqlite3.connect('stok_takip.db')
    cursor = conn.cursor()
  
    try:
        # Yeni sütun ekleme örneği
        cursor.execute("ALTER TABLE urun ADD COLUMN yeni_sutun VARCHAR(100)")
        conn.commit()
        print("Migration successful!")
    except sqlite3.OperationalError as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()
```

## 🚨 Sorun Giderme

### Yaygın Problemler

1. **Database Erişimi**:

   ```python
   # Mutlak path kullanın
   import os
   db_path = os.path.join(os.path.dirname(__file__), 'stok_takip.db')
   conn = sqlite3.connect(db_path)
   ```
2. **Static Files**:

   ```python
   # app.py'de
   app = Flask(__name__, static_folder='static', static_url_path='/static')
   ```
3. **Memory Issues**:

   ```python
   # Database connection'ları kapatın
   try:
       # database operations
   finally:
       conn.close()
   ```

### Performance Optimizasyonu

```python
# app.py'de
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('stok_takip.db')
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.teardown_appcontext
def close_db(error):
    close_db()
```

## 📞 Destek

Deployment ile ilgili sorunlarınız için:

- **Render**: [docs.render.com](https://docs.render.com)
- **Railway**: [docs.railway.app](https://docs.railway.app)
- **Fly.io**: [fly.io/docs](https://fly.io/docs)

---

✅ **Başarılı Deployment İçin Checklist:**

- [ ] requirements.txt güncellendi
- [ ] Secret key production-ready
- [ ] Database path doğru
- [ ] Environment variables ayarlandı
- [ ] Health check endpoint eklendi
- [ ] HTTPS yönlendirmesi aktif
- [ ] Backup stratejisi hazır

🎉 **Tebrikler!** BikeStock sisteminiz artık canlıda!
