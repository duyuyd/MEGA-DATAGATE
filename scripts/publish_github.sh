#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it and run: gh auth login" >&2
  exit 2
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 2
fi

OWNER="$(gh api user --jq .login)"
REPO_NAME="${DATAGATE_REPO_NAME:-MEGA-DATAGATE}"
FULL_NAME="$OWNER/$REPO_NAME"
DESCRIPTION="Local-first data intake: profile, schema drift, contract validation, and safe cleaning."

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b main
fi
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  git branch -M main
fi

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git add -A
  git commit -m "Initial MEGA DataGate MVP 0.1.0"
fi

if gh repo view "$FULL_NAME" >/dev/null 2>&1; then
  echo "Repository already exists: https://github.com/$FULL_NAME"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$FULL_NAME.git"
  fi
  echo "Pushing main to existing repository..."
  git push -u origin main
  exit 0
fi

echo "This will create a NEW PUBLIC repository: https://github.com/$FULL_NAME"
echo "It will not modify or publish MEGA-CHECKER-ULTIMATE."
read -r -p "Type PUBLIC to confirm publication: " CONFIRM
if [[ "$CONFIRM" != "PUBLIC" ]]; then
  echo "Cancelled. No GitHub repository was created."
  exit 0
fi

gh repo create "$FULL_NAME" \
  --public \
  --source . \
  --remote origin \
  --description "$DESCRIPTION" \
  --push

echo
echo "Published: https://github.com/$FULL_NAME"
echo "Next: check Actions and open the README in the repository."
