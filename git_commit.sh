#!/bin/bash
# Git commit and push script

echo ""
echo "================================"
echo "Fundamental Data Pipeline"
echo "Git Commit Script"
echo "================================"
echo ""

# Configure git
git config user.name "Development Team"
git config user.email "dev@fundamental-pipeline.local"

echo "Adding all files..."
git add -A

echo ""
echo "Committing changes..."
git commit -F COMMIT_MESSAGE.txt

echo ""
echo "Commit completed!"
echo ""

# Ask if user wants to push
read -p "Would you like to push to remote? (y/n) " push_choice

if [ "$push_choice" = "y" ] || [ "$push_choice" = "Y" ]; then
    echo ""
    echo "Pushing to remote..."
    git push
    echo ""
    echo "Push completed!"
else
    echo ""
    echo "Skipping push. You can push later with: git push"
fi

echo ""
echo "Done!"

