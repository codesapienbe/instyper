#!/usr/bin/env -S uv run
import os
import platform
import subprocess
import shutil

# --- Ensure ~/.instyper and models are set up before build ---
USER_HOME = os.path.expanduser('~')
USER_INSTYPER_DIR = os.path.join(USER_HOME, '.instyper')
USER_MODELS_DIR = os.path.join(USER_INSTYPER_DIR, 'models')
REPO_BASE = os.path.dirname(os.path.abspath(__file__))
REPO_MODELS_DIR = os.path.join(REPO_BASE, 'models')
REPO_README = os.path.join(REPO_BASE, 'README.md')
USER_README = os.path.join(USER_INSTYPER_DIR, 'README.md')

os.makedirs(USER_MODELS_DIR, exist_ok=True)

# Copy README.md to ~/.instyper if not already present
if os.path.isfile(REPO_README) and not os.path.isfile(USER_README):
    shutil.copy2(REPO_README, USER_README)

# If ~/.instyper/models is empty and repo models/ exists, copy all models
if not os.listdir(USER_MODELS_DIR) and os.path.isdir(REPO_MODELS_DIR):
    for item in os.listdir(REPO_MODELS_DIR):
        src = os.path.join(REPO_MODELS_DIR, item)
        dst = os.path.join(USER_MODELS_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)

# --- End setup ---

def build_for_platform():
    system = platform.system()
    
    # Basic PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", f"instyper-{system.lower()}",
        "--add-data", "README.md;." if system == "Windows" else "README.md:.",
        "src/instyper/__init__.py"
    ]
    
    # Platform-specific options
    if system == "Darwin":  # macOS
        cmd.extend(["--windowed"])
    elif system == "Windows":
        cmd.extend(["--windowed"])
    
    # Run PyInstaller
    subprocess.run(cmd)
    
    print(f"Build completed for {system}. Executable is in the 'dist' directory.")

if __name__ == "__main__":
    # Install dependencies first
    subprocess.run(["uv", "sync"])
    
    # Build the executable
    build_for_platform()
