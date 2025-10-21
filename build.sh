#!/bin/bash
echo "🚀 Starting build process..."
pip install --upgrade pip
pip install -r requirements.txt
echo "📦 Dependencies installed"
python safe_upgrade_database.py
echo "✅ Database setup complete"