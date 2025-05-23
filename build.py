import os
import subprocess
import sys

REPO_BASE = os.path.dirname(os.path.abspath(__file__))
PYOXIDIZER_BZL = os.path.join(REPO_BASE, "pyoxidizer.bzl")

# 1. Write a minimal pyoxidizer.bzl if not present
if not os.path.isfile(PYOXIDIZER_BZL):
    with open(PYOXIDIZER_BZL, "w", encoding="utf-8") as f:
        f.write('''
# PyOxidizer config for Instyper
python_config = default_python_config()
packaging_policy = default_packaging_policy()
packaging_policy.bytecode_optimize_level = 1

dist = python_distribution(
    name = "instyper",
    config = python_config,
    packaging_policy = packaging_policy,
    files = [
        "src/instyper"
    ],
    entry_point = "instyper:main"
)
''')

# 2. Run PyOxidizer build
def run_pyoxidizer():
    print("Running PyOxidizer build...")
    result = subprocess.run(["pyoxidizer", "build"], cwd=REPO_BASE)
    if result.returncode != 0:
        print("PyOxidizer build failed.")
        sys.exit(1)
    print("PyOxidizer build completed.")

if __name__ == "__main__":
    run_pyoxidizer() 