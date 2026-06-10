#!/usr/bin/env python3
"""
Strata Wiki - Google Drive Pull Script
Exports Google Docs to markdown and saves into ~/strata-wiki/raw/
"""

import os
import subprocess
import tempfile
import json
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
WIKI_ROOT = Path.home() / "strata-wiki"

# All docs found in Drive search, organized by raw/ subfolder
DOCS = {
    "clients/avoca": [
        {"id": "1BEH7xb_HaYT57Ghlxe-0PjopB5t4aHOR", "name": "avoca-messaging"},
        {"id": "1B25CZrOyO7L8gkGX-NboTb18ynQgdfvu", "name": "avoca-pitch-deck"},
    ],
    "clients/unity-industry": [
        {"id": "1BRZHu36j9RJo1napSlsxlcF7Tx-7XNue", "name": "unity-industry-deliverables"},
        {"id": "1cXKj_VpuIMPSUIxZ8Eu7rzRgL-Yddgj1", "name": "unity-industry-pov-messaging"},
    ],
    "clients/unity-games": [
        {"id": "17W73fIp_9mb4hWRz_2apsScxg_dkUpqJ", "name": "unity-games-deliverables"},
    ],
    "clients/teamohana": [
        {"id": "1myl8KFmQvRd-jB4XFwGS3zicNSbO2rRG", "name": "teamohana-deliverables"},
        {"id": "1r3CCCBN9iolkOydZLWTzrYal24gRcXnX", "name": "teamohana-messaging-framework"},
        {"id": "1lnublRqgww0mitGWnJygpWCe9tDBkKbc", "name": "teamohana-pov"},
    ],
    "clients/agency": [
        {"id": "1JlQG87EMMQ2itgUbLBYfwXU48gjlHOat", "name": "agency-deliverables"},
    ],
    "clients/general-legal": [
        {"id": "1S3F4zOUGEf2K9SKany5wttYPWWhd3Byp", "name": "general-legal-deliverables"},
    ],
    "frameworks": [
        {"id": "1KRws5ZnLWjmV7jvCJezrASHDlZCJ5NKZ", "name": "messaging-framework-template"},
        {"id": "1Vk-6rMB_hEDYy1fEwgHzSvZIGsbJJR1L", "name": "pitch-deck-framework"},
        {"id": "1ephGsFHWmJihakstIv8ZLcn-xrCHCLDd", "name": "messaging-framework-v2"},
        {"id": "1zf_Q30Y_gBNlej5e9MvEeqj_TD6nVBo0", "name": "narrative-framework"},
    ],
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def export_doc_as_markdown(doc_id: str, dest_path: Path) -> bool:
    """
    Export a Google Doc to markdown via the Drive export URL.
    Uses curl (no OAuth needed for docs shared with the authenticated user
    via the browser session). Falls back to docx->pandoc conversion.
    """
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=docx"

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download as docx
        result = subprocess.run(
            ["curl", "-L", "-s", "-o", tmp_path,
             "--cookie-jar", "/tmp/gdrive_cookies.txt",
             "--cookie", "/tmp/gdrive_cookies.txt",
             export_url],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print(f"  ✗ curl failed: {result.stderr}")
            return False

        # Check we got a real docx (not an HTML error page)
        file_size = os.path.getsize(tmp_path)
        if file_size < 1000:
            print(f"  ✗ File too small ({file_size}b) - likely auth error")
            return False

        # Convert docx -> markdown with pandoc
        md_result = subprocess.run(
            ["pandoc", tmp_path, "-t", "markdown", "-o", str(dest_path),
             "--wrap=none", "--strip-comments"],
            capture_output=True, text=True, timeout=30
        )

        if md_result.returncode != 0:
            print(f"  ✗ pandoc failed: {md_result.stderr}")
            return False

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def pull_all():
    print("🚀 Strata Wiki - Pulling Google Drive docs\n")

    success = 0
    failed = []

    for folder, docs in DOCS.items():
        dest_dir = WIKI_ROOT / "raw" / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 {folder}/")

        for doc in docs:
            dest_path = dest_dir / f"{doc['name']}.md"
            print(f"  → {doc['name']}...", end=" ", flush=True)

            if export_doc_as_markdown(doc["id"], dest_path):
                size = dest_path.stat().st_size
                print(f"✓ ({size:,} bytes)")
                success += 1
            else:
                print("✗ FAILED")
                failed.append(f"{folder}/{doc['name']}")

    print(f"\n{'─'*50}")
    print(f"✓ {success} docs pulled successfully")

    if failed:
        print(f"✗ {len(failed)} failed:")
        for f in failed:
            print(f"  - {f}")
        print("\nFailed docs need to be exported manually from Google Drive.")
        print("File → Download → Plain Text (.txt) then rename to .md")
    else:
        print("All docs pulled. Ready to compile the wiki.")

    # Git commit the new raw files
    if success > 0:
        print("\n📝 Committing to git...")
        subprocess.run(
            ["git", "-C", str(WIKI_ROOT), "add", "raw/"],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(WIKI_ROOT), "commit", "-m",
             f"raw: pull {success} docs from Google Drive"],
            capture_output=True
        )
        print("Done.")


if __name__ == "__main__":
    pull_all()
