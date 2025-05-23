import os
import sys
import shutil
import platform
from pathlib import Path

# --- CONFIG ---
APP_NAME = "Instyper"
BINARY_NAME = "instyper-windows.exe" if platform.system() == "Windows" else "instyper"
REPO_DIST_BINARY = os.path.join("dist", BINARY_NAME)
REPO_MODELS_DIR = os.path.join("src", "models")
REPO_README = "README.md"
USER_HOME = str(Path.home())
USER_INSTYPER_DIR = os.path.join(USER_HOME, ".instyper")
USER_MODELS_DIR = os.path.join(USER_INSTYPER_DIR, "models")
USER_README = os.path.join(USER_INSTYPER_DIR, "README.md")

# --- Install locations ---
if platform.system() == "Windows":
    INSTALL_BIN_DIR = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), APP_NAME)
    INSTALL_BIN_PATH = os.path.join(INSTALL_BIN_DIR, "instyper.exe")
    DESKTOP_PATH = os.path.join(USER_HOME, "Desktop")
    START_MENU_PATH = os.path.join(USER_HOME, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
    SHORTCUT_PATH = os.path.join(DESKTOP_PATH, f"{APP_NAME}.lnk")
    START_MENU_SHORTCUT = os.path.join(START_MENU_PATH, f"{APP_NAME}.lnk")
else:
    INSTALL_BIN_DIR = "/usr/local/bin"
    INSTALL_BIN_PATH = os.path.join(INSTALL_BIN_DIR, "instyper")
    DESKTOP_PATH = os.path.join(USER_HOME, "Desktop")
    SHORTCUT_PATH = os.path.join(DESKTOP_PATH, f"{APP_NAME}.desktop")

# --- Helper functions ---
def copytree(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def create_windows_shortcut(target, shortcut_path):
    import pythoncom
    from win32com.shell import shell, shellcon
    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    shortcut.SetPath(target)
    shortcut.SetDescription(APP_NAME)
    shortcut.SetIconLocation(target, 0)
    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(shortcut_path, 0)

def create_linux_desktop_shortcut(target, shortcut_path):
    content = f"""[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec={target}\nIcon=utilities-terminal\nTerminal=false\n"""
    with open(shortcut_path, "w") as f:
        f.write(content)
    os.chmod(shortcut_path, 0o755)

# --- Wizard Steps ---
def main():
    print(f"{APP_NAME} Installer Wizard\n{'='*30}")
    print(f"Installing to default locations...")

    # 1. Copy binary
    print(f"Copying binary to {INSTALL_BIN_PATH} ...")
    os.makedirs(INSTALL_BIN_DIR, exist_ok=True)
    shutil.copy2(REPO_DIST_BINARY, INSTALL_BIN_PATH)

    # 2. Copy models
    print(f"Copying models to {USER_MODELS_DIR} ...")
    os.makedirs(USER_MODELS_DIR, exist_ok=True)
    for item in os.listdir(REPO_MODELS_DIR):
        src = os.path.join(REPO_MODELS_DIR, item)
        dst = os.path.join(USER_MODELS_DIR, item)
        if os.path.isdir(src):
            copytree(src, dst)

    # 3. Copy README
    print(f"Copying README to {USER_README} ...")
    shutil.copy2(REPO_README, USER_README)

    # 4. Create shortcuts
    print("Creating desktop and start menu shortcuts ...")
    if platform.system() == "Windows":
        try:
            import pythoncom
            import win32com.client
            shell = win32com.client.Dispatch('WScript.Shell')
            # Desktop shortcut
            shortcut = shell.CreateShortCut(SHORTCUT_PATH)
            shortcut.Targetpath = INSTALL_BIN_PATH
            shortcut.WorkingDirectory = INSTALL_BIN_DIR
            shortcut.IconLocation = INSTALL_BIN_PATH
            shortcut.save()
            # Start menu shortcut
            os.makedirs(START_MENU_PATH, exist_ok=True)
            shortcut2 = shell.CreateShortCut(START_MENU_SHORTCUT)
            shortcut2.Targetpath = INSTALL_BIN_PATH
            shortcut2.WorkingDirectory = INSTALL_BIN_DIR
            shortcut2.IconLocation = INSTALL_BIN_PATH
            shortcut2.save()
            print(f"Shortcuts created on Desktop and Start Menu.")
        except Exception as e:
            print(f"Failed to create Windows shortcuts: {e}")
    else:
        # Linux/macOS desktop shortcut
        try:
            create_linux_desktop_shortcut(INSTALL_BIN_PATH, SHORTCUT_PATH)
            print(f"Desktop shortcut created at {SHORTCUT_PATH}.")
        except Exception as e:
            print(f"Failed to create desktop shortcut: {e}")

    print("\nInstallation complete! You can now launch Instyper from your Desktop or Start Menu.")

if __name__ == "__main__":
    main() 