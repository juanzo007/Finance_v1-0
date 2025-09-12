import subprocess
import sys
import glob

print("=== Checking pipeline and extractors for syntax errors ===")

files = ["finances_pipeline.py"] + glob.glob("scripts/image-scripts/*.py")
result = subprocess.run([sys.executable, "-m", "py_compile", *files])

if result.returncode == 0:
    print("✅ All scripts compiled cleanly")
else:
    print("❌ One or more scripts have syntax errors (see above)")
