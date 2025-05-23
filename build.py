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

def build_for_all_platforms():
    # Note: True cross-compilation is not supported by PyInstaller. This script assumes you run it on each OS or use CI runners.
    platforms = [
        ("Windows", "instyper-windows", ["--windowed"]),
        ("Darwin", "instyper-darwin", ["--windowed"]),
        ("Linux", "instyper-linux", []),
    ]
    for system, exe_name, extra_opts in platforms:
        print(f"\n=== Building for {system} ===")
        cmd = [
            "pyinstaller",
            "--onefile",
            "--name", exe_name,
            "--add-data", "README.md;." if system == "Windows" else "README.md:.",
            "src/instyper/__init__.py"
        ]
        cmd.extend(extra_opts)
        # Only build for the current platform unless running in a CI matrix
        if platform.system() != system:
            print(f"Skipping build for {system} (run this script on a {system} machine or use CI for cross-platform builds)")
            continue
        subprocess.run(cmd)
        print(f"Build completed for {system}. Executable is in the 'dist' directory.")
        if system == "Windows":
            # Generate Inno Setup script
            iss_content = f'''
[Setup]
AppName=instyper
AppVersion=0.1.0
DefaultDirName={{pf}}\\instyper
DefaultGroupName=instyper
OutputDir=dist
OutputBaseFilename=instyper-windows-setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\\instyper-windows.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: isreadme

[Icons]
Name: "{{group}}\\instyper"; Filename: "{{app}}\\instyper-windows.exe"
Name: "{{commondesktop}}\\instyper"; Filename: "{{app}}\\instyper-windows.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons"; Flags: unchecked
'''
            iss_path = os.path.join(REPO_BASE, "instyper-windows.iss")
            with open(iss_path, "w", encoding="utf-8") as f:
                f.write(iss_content)
            # Try to run Inno Setup Compiler (iscc.exe) if available
            iscc_path = r"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
            if os.path.isfile(iscc_path):
                subprocess.run([iscc_path, iss_path])
            else:
                print(f"Inno Setup Compiler not found at {iscc_path}. Please compile {iss_path} manually using Inno Setup.")
        if system == "Darwin":
            # Generate a basic pkgbuild script for macOS
            pkgbuild_script = f'''#!/bin/bash
set -e
APP_NAME="instyper-darwin"
VERSION="0.1.0"
BUILD_DIR="dist"
PKG_DIR="$BUILD_DIR/$APP_NAME.pkgdir"
INSTALL_PATH="/Applications/instyper"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR$INSTALL_PATH"
cp "$BUILD_DIR/$APP_NAME" "$PKG_DIR$INSTALL_PATH/"
cp "README.md" "$PKG_DIR$INSTALL_PATH/"

pkgbuild \
  --root "$PKG_DIR" \
  --identifier "com.instyper.app" \
  --version "$VERSION" \
  --install-location "/" \
  "$BUILD_DIR/instyper-darwin-$VERSION.pkg"
'''
            script_path = os.path.join(REPO_BASE, "build-macos-pkg.sh")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(pkgbuild_script)
            os.chmod(script_path, 0o755)
            print(f"macOS .pkg build script generated at {script_path}. Run it on a Mac with Xcode command line tools installed.")
        if system == "Linux":
            # Generate a basic .deb packaging script for Linux
            deb_script = f'''#!/bin/bash
set -e
APP_NAME="instyper-linux"
VERSION="0.1.0"
BUILD_DIR="dist"
PKG_DIR="$BUILD_DIR/$APP_NAME.debpkg"
DEBIAN_DIR="$PKG_DIR/DEBIAN"
INSTALL_PATH="/opt/instyper"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR$INSTALL_PATH"
mkdir -p "$DEBIAN_DIR"
cp "$BUILD_DIR/$APP_NAME" "$PKG_DIR$INSTALL_PATH/"
cp "README.md" "$PKG_DIR$INSTALL_PATH/"
echo "Package: instyper\nVersion: $VERSION\nSection: base\nPriority: optional\nArchitecture: amd64\nMaintainer: Your Name <you@example.com>\nDescription: Instyper application" > "$DEBIAN_DIR/control"
dpkg-deb --build "$PKG_DIR" "$BUILD_DIR/instyper-linux-$VERSION.deb"
'''
            script_path = os.path.join(REPO_BASE, "build-linux-deb.sh")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(deb_script)
            os.chmod(script_path, 0o755)
            print(f"Linux .deb build script generated at {script_path}. Run it on a Linux system with dpkg-deb installed.")

if __name__ == "__main__":
    # Install dependencies first
    subprocess.run(["uv", "sync"])
    # Build the executables for all platforms
    build_for_all_platforms()
