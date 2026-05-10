#!/bin/bash
# Deploy script for Celebrity Tracker Dashboard

echo "🚀 Celebrity Tracker Dashboard Deploy Script"
echo ""

# Check if git repo exists
if [ ! -d ".git" ]; then
    echo "1️⃣ Initializing Git repo..."
    git init
    git add .
    git commit -m "Initial dashboard deployment"
fi

echo ""
echo "2️⃣ Next steps:"
echo ""
echo "   A. Create GitHub repo:"
echo "      - Go to https://github.com/new"
echo "      - Name it 'celebrity-tracker' (or whatever)"
echo "      - Keep it Public"
echo ""
echo "   B. Push code:"
echo "      git remote add origin https://github.com/YOUR_USERNAME/celebrity-tracker.git"
echo "      git branch -M main"
echo "      git push -u origin main"
echo ""
echo "   C. Deploy to Streamlit:"
echo "      - Go to https://streamlit.io/cloud"
echo "      - Sign in with GitHub"
echo "      - Click 'New app'"
echo "      - Select your repo"
echo "      - Main file: app.py"
echo "      - Click Deploy!"
echo ""
echo "✅ Done! Your dashboard will be live at:"
echo "   https://celebrity-tracker-yourname.streamlit.app"
echo ""
