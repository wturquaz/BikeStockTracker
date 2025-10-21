# BikeStock - AI Coding Instructions

## Project Overview
BikeStock is a **multi-warehouse bicycle inventory management system** built with Flask, SQLite, and Bootstrap. The system manages stock across multiple warehouses with barcode support, user authentication, and detailed transaction history.

## Architecture & Core Patterns

### Database Design
- **Single SQLite file**: `stok_takip.db` with strict foreign key relationships
- **Multi-warehouse model**: Each product can have different stock levels per warehouse (`urun_stok` table)
- **Audit trail**: All operations logged in `islem_gecmisi` with user attribution

### Key Entity Relationships
```
urun (products) → urun_stok (stock per warehouse) ← depo (warehouses)
kullanici (users) → islem_gecmisi (transaction history)
```

### Database Migration Strategy
- **Never use `setup_database.py`** in production (deletes existing data)
- **Always use `safe_upgrade_database.py`** for deployments (preserves data)
- **Local development**: Use `upgrade_database.py` for schema updates

## Critical Workflows

### Database Operations
```bash
# Production deployment
python safe_upgrade_database.py

# Local development
python upgrade_database.py

# Fresh install only
python setup_database.py  # WARNING: Deletes all data
```

### Running the Application
```bash
# Development
python app.py

# Production
gunicorn app:app --config gunicorn_config.py
```

## Flask Application Structure

### Authentication Pattern
- **Session-based auth**: `login_required` decorator on all protected routes
- **Role-based access**: Admin/user roles stored in session
- **Password security**: SHA-256 hashing with `hashlib`

### Route Organization
- **Main routes**: Authentication, dashboard (`/`)
- **Stock operations**: `/stok` (list), `/stok_cikisi` (outbound), `/transfer` (inter-warehouse)
- **AJAX endpoints**: `/api/urun_ara` (product search), `/api/urun_stok_durumu` (stock status)

### Error Handling Convention
```python
# Standard pattern for database operations
try:
    # Database operations
    conn.commit()
    flash('Success message', 'success')
except Exception as e:
    flash(f'Error: {str(e)}', 'error')
finally:
    conn.close()
```

## Frontend Patterns

### Template Inheritance
- **Base template**: `templates/base.html` with Bootstrap 5 + jQuery
- **Turkish language**: All UI text in Turkish
- **Responsive design**: Mobile-first approach

### AJAX Search Implementation
- **Product search**: Real-time search by name or barcode (`/api/urun_ara`)
- **Stock lookup**: Dynamic warehouse stock display (`/api/urun_stok_durumu`)
- **Pattern**: jQuery autocomplete with debouncing

## Development Conventions

### Database Connection
```python
# Standard pattern - always use this
def get_db_connection():
    conn = sqlite3.connect('stok_takip.db')
    conn.row_factory = sqlite3.Row  # Essential for dict-like access
    return conn
```

### Transaction Logging
Every stock operation must create an `islem_gecmisi` record with:
- `islem_tipi`: Operation type (STOK_CIKIS, TRANSFER, etc.)
- `urun_bilgisi`: Human-readable description
- `eski_deger`/`yeni_deger`: Before/after values
- User attribution from session

### Form Validation Pattern
1. Server-side validation in route handlers
2. Flash messages for user feedback
3. Redirect-after-POST pattern to prevent duplicate submissions

## Deployment Configuration

### Platform-Specific Setup
- **Render.com**: Uses `render.yaml` + `safe_upgrade_database.py` in build
- **Railway.app**: Uses `railway.json` + `upgrade_database.py` in deploy
- **Gunicorn**: Single worker configuration for SQLite compatibility

### Environment Variables
- `SECRET_KEY`: Auto-generated in production, fallback to `secrets.token_hex(16)`

## Key Files to Understand

- `app.py`: Main Flask application (843 lines) - contains all routes and business logic
- `safe_upgrade_database.py`: Production-safe database migrations
- `templates/base.html`: UI framework and JavaScript patterns
- `templates/stok_listesi.html`: Example of warehouse-aware data display

## Common Gotchas

1. **SQLite limitations**: Single writer, use `conn.close()` in finally blocks
2. **Warehouse context**: Most operations require `depo_id` parameter
3. **Turkish characters**: Ensure UTF-8 encoding in all files
4. **Session management**: Check `kullanici_id` in session for auth state
5. **Stock validation**: Always verify available stock before stock outbound operations