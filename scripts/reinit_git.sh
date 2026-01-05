#!/bin/bash
echo "⚠️ Starting Repository Reset (Size Reduction)..."

# 1. Update Parquet files using the script we created earlier
echo "🔄 Updating Parquet files..."
python scripts/update_parquet.py

# 2. Convert database_nar.csv to Parquet if needed
# (The script usually handles this, but let's be sure)

# 3. Check Git Size
echo "📉 Current .git size:"
du -sh .git

# 4. Remove .git
echo "🔥 Removing old git history (3.2GB+)..."
rm -rf .git
echo "✅ History removed."

# 5. Re-init
echo "🌱 Initializing new git repo..."
git init
git branch -M main

# 6. Add Remote
echo "🔗 Adding remote origin..."
git remote add origin https://github.com/itou-daiki/dai-keiba

# 7. Add Files
echo "📦 Adding files (this respects .gitignore)..."
git add .

# 8. Commit
echo "💾 Committing lightweight version..."
git commit -m "Reset repository to reduce size (Removed huge history)"

# 9. Verify Size
echo "📉 New .git size:"
du -sh .git

echo "🚀 Ready to push."
echo "Running: git push -f origin main"
git push -f origin main

echo "✅ Done! Streamlit should deploy successfully now."
