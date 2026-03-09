#!/usr/bin/env bash
set -euo pipefail

# Repairs common push issues around generated binary workbook artifacts.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="spreadsheet_model/hyperion_spreadsheet_model.xlsx"

echo "[1/6] Ensure ignore rule exists"
grep -q "^${TARGET}$" .gitignore || echo "$TARGET" >> .gitignore

echo "[2/6] Remove workbook from index if currently tracked"
if git ls-files --error-unmatch "$TARGET" >/dev/null 2>&1; then
  git rm --cached "$TARGET"
else
  echo "  - not tracked in index"
fi

echo "[3/6] Remove local generated workbook (can be regenerated)"
rm -f "$TARGET"

echo "[4/6] Regenerate workbook locally (untracked artifact)"
python3 spreadsheet_model/build_workbook.py >/dev/null

echo "[5/6] Show attrs and LFS status"
git check-attr --all -- "$TARGET" || true
git lfs ls-files || true

echo "[6/6] Repo status"
git status --short

echo "Done. Commit .gitignore/other text changes and push again."
