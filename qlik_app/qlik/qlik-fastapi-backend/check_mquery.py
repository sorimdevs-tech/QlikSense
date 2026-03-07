"""
check_mquery.py
───────────────
Run this script on your server BEFORE starting main.py to verify the 
correct mquery_converter.py is in place.

Usage:
    python check_mquery.py

If it prints ✅ PASS for all checks → your server will generate correct SharePoint M Queries.
If it prints ❌ FAIL → follow the instructions printed to fix it.
"""

import sys
import os

print("=" * 60)
print("  mquery_converter.py DIAGNOSTIC CHECK")
print("=" * 60)

# ── 1. Find the file ──────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
target_file = os.path.join(script_dir, "mquery_converter.py")

print(f"\n[1] Looking for: {target_file}")
if os.path.exists(target_file):
    print(f"    ✅ File exists")
else:
    print(f"    ❌ FILE NOT FOUND!")
    print(f"    → Copy the fixed mquery_converter.py to: {script_dir}")
    sys.exit(1)

# ── 2. Check it has the SharePoint fix ───────────────────────
with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

checks = [
    ("SharePoint.Files(", "SharePoint.Files() function present"),
    ("_is_sharepoint_url", "_is_sharepoint_url() helper present"),
    ("_strip_qlik_qualifier", "_strip_qlik_qualifier() helper present"),
    ("_build_sharepoint_m", "_build_sharepoint_m() builder present"),
]

all_ok = True
print("\n[2] Checking file contents:")
for token, desc in checks:
    if token in content:
        print(f"    ✅ {desc}")
    else:
        print(f"    ❌ MISSING: {desc}")
        all_ok = False

if not all_ok:
    print("\n    → You have the OLD mquery_converter.py. Replace it with the fixed version.")
    sys.exit(1)

# ── 3. Import and actually test it ───────────────────────────
print("\n[3] Importing and testing conversion:")
try:
    # Force reload in case old version was cached
    if "mquery_converter" in sys.modules:
        del sys.modules["mquery_converter"]
    
    sys.path.insert(0, script_dir)
    from mquery_converter import MQueryConverter, _is_sharepoint_url

    table = {
        "name": "Model_Master",
        "source_type": "csv",
        "source_path": "Model_Master.csv",
        "fields": [
            {"name": "Model_Master.ModelID", "type": "string"},
            {"name": "ModelName", "type": "string"},
        ],
        "options": {}
    }
    base_path = "https://sorimtechnologies.sharepoint.com/sites/ddrive"

    converter = MQueryConverter()
    m_expr, _ = converter._dispatch(table, base_path, None)

    test_results = [
        ("SharePoint.Files" in m_expr,       "Uses SharePoint.Files()"),
        ("File.Contents" not in m_expr,      "Does NOT use File.Contents()"),
        ("FilePath = https://" not in m_expr, "No unquoted URL (no syntax error)"),
        ('"ModelID"' in m_expr,              'Column "ModelID" (not "Model_Master.ModelID")'),
        (_is_sharepoint_url(base_path),       "SharePoint URL correctly detected"),
    ]

    for passed, desc in test_results:
        status = "✅" if passed else "❌"
        print(f"    {status} {desc}")
        if not passed:
            all_ok = False

except Exception as e:
    print(f"    ❌ IMPORT/RUN ERROR: {e}")
    all_ok = False

# ── 4. Result ─────────────────────────────────────────────────
print("\n" + "=" * 60)
if all_ok:
    print("  ✅ ALL CHECKS PASSED — safe to start main.py")
    print("=" * 60)
    print("\nGenerated M Query preview:")
    print("-" * 40)
    print(m_expr)
else:
    print("  ❌ CHECKS FAILED — DO NOT start main.py yet")
    print("=" * 60)
    print("\nFIX STEPS:")
    print("  1. Copy the fixed mquery_converter.py to your project folder")
    print("  2. Run this script again to verify")
    print("  3. Then start: python main.py")
    sys.exit(1)