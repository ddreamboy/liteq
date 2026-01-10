#!/bin/bash

# Script to release a new version of liteq
# Usage: ./release.sh [version]
# Example: ./release.sh 0.1.2

set -e  # Exit on error

# Detect platform and set Python path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]] || command -v python.exe &> /dev/null; then
    # Windows (Git Bash or similar)
    PYTHON="venv/Scripts/python.exe"
else
    # Unix-like (Linux, macOS)
    PYTHON="venv/bin/python"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from pyproject.toml if not provided
if [ -z "$1" ]; then
    VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    echo -e "${YELLOW}No version provided, using version from pyproject.toml: ${VERSION}${NC}"
else
    VERSION=$1
    echo -e "${GREEN}Releasing version: ${VERSION}${NC}"
    
    # Update version in pyproject.toml
    sed -i "s/^version = .*/version = \"${VERSION}\"/" pyproject.toml
    echo -e "${GREEN}[+] Updated version in pyproject.toml${NC}"
fi

# Check if git working directory is clean
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}Warning: Working directory is not clean. Uncommitted changes:${NC}"
    git status -s
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
"$PYTHON" -m pytest -v
echo -e "${GREEN}[+] Tests passed${NC}"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info
echo -e "${GREEN}[+] Cleaned${NC}"

# Build package
echo -e "${YELLOW}Building package...${NC}"
"$PYTHON" -m build
echo -e "${GREEN}[+] Package built${NC}"

# Commit version change if it was updated
if [ -n "$1" ]; then
    git add pyproject.toml
    if git diff --cached --quiet; then
        echo -e "${YELLOW}No changes to commit (version already updated)${NC}"
    else
        git commit -m "Bump version to ${VERSION}"
        echo -e "${GREEN}[+] Committed version change${NC}"
    fi
fi

# Create git tag
echo -e "${YELLOW}Creating git tag v${VERSION}...${NC}"
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
echo -e "${GREEN}[+] Git tag created${NC}"

# Get current branch name
BRANCH=$(git branch --show-current)

# Push to GitHub
echo -e "${YELLOW}Pushing to GitHub (branch: ${BRANCH})...${NC}"
git push origin "${BRANCH}"
git push origin "v${VERSION}"
echo -e "${GREEN}[+] Pushed to GitHub${NC}"

# Ask before publishing to PyPI
echo -e "${YELLOW}Ready to publish to PyPI.${NC}"
read -p "Publish to PyPI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Upload to PyPI
    echo -e "${YELLOW}Publishing to PyPI...${NC}"
    "$PYTHON" -m twine upload dist/*
    echo -e "${GREEN}[+] Published to PyPI${NC}"
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}[!] Release ${VERSION} completed successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "PyPI: https://pypi.org/project/liteq/${VERSION}/"
    echo -e "GitHub: https://github.com/ddreamboy/liteq/releases/tag/v${VERSION}"
else
    echo -e "${YELLOW}Skipped PyPI publication.${NC}"
    echo -e "${GREEN}Git tag v${VERSION} created and pushed.${NC}"
    echo -e "To publish later, run: ${YELLOW}python -m twine upload dist/*${NC}"
fi
