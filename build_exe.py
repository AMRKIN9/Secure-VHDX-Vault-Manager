import subprocess
import sys
import os

def build():
    print("=" * 60)
    print("  SECURE // VHDX VAULT MANAGER - COMPILATION PIPELINE")
    print("=" * 60)
    print("[*] Initiating PyInstaller standalone one-file compilation...")
    print("[*] Target: Windows x64 Portable Executable (Zero External Dependencies)")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--icon", "icon.ico",
        "--add-data", "icon.ico;.",
        "--add-data", "icon.png;.",
        "--collect-all", "customtkinter",
        "--collect-all", "qrcode",
        "--collect-all", "PIL",
        "--name", "SecureVaultManager",
        "main.py"
    ]
    
    res = subprocess.run(cmd)
    if res.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "SecureVaultManager.exe"))
        print("\n" + "=" * 60)
        print(f"[+] BUILD SUCCESSFUL!")
        print(f"[+] Portable Binary: {exe_path}")
        print("=" * 60)
    else:
        print(f"\n[-] Build failed with exit code {res.returncode}")

if __name__ == "__main__":
    build()
