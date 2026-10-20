import os
import glob
import time
import shutil
from typing import List, Optional, Tuple
from models import Container
from powershell import run_ps, run_ps_json
import bitlocker
import logging
import subprocess
import re

DEFAULT_STORAGE_DIR = os.path.join(os.environ.get("USERPROFILE", "."), "SecureContainers")

def get_storage_dir() -> str:
    from auth_2fa import SecurityManager
    sm = SecurityManager()
    custom_dir = sm.config.get("custom_vault_dir")
    if custom_dir and os.path.exists(custom_dir):
        return custom_dir
    if not os.path.exists(DEFAULT_STORAGE_DIR):
        os.makedirs(DEFAULT_STORAGE_DIR, exist_ok=True)
    return DEFAULT_STORAGE_DIR

def ensure_storage_dir():
    s_dir = get_storage_dir()
    if not os.path.exists(s_dir):
        os.makedirs(s_dir, exist_ok=True)

def run_diskpart(commands: str) -> str:
    """Runs diskpart securely via subprocess without console window."""
    creationflags = 0
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        creationflags = subprocess.CREATE_NO_WINDOW
        
    logging.debug(f"Running diskpart commands:\n{commands}")
    res = subprocess.run(
        ["diskpart"], 
        input=commands, 
        capture_output=True, 
        text=True, 
        creationflags=creationflags
    )
    
    if res.returncode != 0 or "DiskPart has encountered an error" in res.stdout:
        logging.error(f"Diskpart error:\n{res.stdout}\n{res.stderr}")
        raise RuntimeError(f"Diskpart error:\n{res.stdout}")
    return res.stdout

def _get_vhd_info(path: str) -> Tuple[bool, Optional[str]]:
    """Returns (is_mounted: bool, drive_letter: str|None). Uses PowerShell with diskpart fallback."""
    # Fast path via PowerShell Get-Disk / Get-Partition
    normalized_path = os.path.abspath(path).replace("'", "''")
    ps_query = f"""
    $vhd = Get-VHD -Path '{normalized_path}' -ErrorAction SilentlyContinue
    if ($vhd -and $vhd.Attached) {{
        $disk = Get-Disk | Where-Object {{$_.Location -like "*{os.path.basename(path)}*" -or $_.FriendlyName -eq "Msft Virtual Disk"}}
        # fallback to diskpart if needed
    }}
    """
    
    # Using diskpart query which is standard on all Windows editions
    try:
        out = run_diskpart(f'select vdisk file="{path}"\ndetail vdisk\n')
        match = re.search(r"Associated disk#:\s*(\d+)", out)
        if not match:
            return False, None
            
        disk_num = match.group(1)
        out_disk = run_diskpart(f'select disk {disk_num}\ndetail disk\n')
        
        for line in out_disk.splitlines():
            line = line.strip()
            if line.startswith("Volume"):
                parts = line.split()
                if len(parts) >= 3:
                    if len(parts[2]) == 1 and parts[2].isalpha():
                        return True, parts[2].upper() + ":"
                    if len(parts[3]) == 1 and parts[3].isalpha():
                        return True, parts[3].upper() + ":"
        return True, None
    except Exception as e:
        logging.warning(f"Failed to query detail vdisk for {path}: {e}")
        return False, None

def list_containers() -> List[Container]:
    """Scans the storage directory and returns a rich list of Container objects."""
    ensure_storage_dir()
    s_dir = get_storage_dir()
    containers = []
    
    for vhdx_file in glob.glob(os.path.join(s_dir, "*.vhdx")):
        name = os.path.basename(vhdx_file)
        size_gb = round(os.path.getsize(vhdx_file) / (1024**3), 2)
        created_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getctime(vhdx_file)))
        
        is_mounted, drive_letter = _get_vhd_info(vhdx_file)
        bl_status = "Off"
        used_gb = None
        free_gb = None
        usage_pct = None
        
        if is_mounted and drive_letter:
            bl_status = bitlocker.get_volume_status(drive_letter)
            if bl_status != "Locked":
                try:
                    usage = shutil.disk_usage(drive_letter + "\\")
                    total = usage.total / (1024**3)
                    used = usage.used / (1024**3)
                    free = usage.free / (1024**3)
                    used_gb = round(used, 2)
                    free_gb = round(free, 2)
                    usage_pct = round((used / total) * 100, 1) if total > 0 else 0.0
                except Exception:
                    pass
                
        containers.append(Container(
            name=name,
            path=vhdx_file,
            size_gb=size_gb,
            is_mounted=is_mounted,
            drive_letter=drive_letter,
            bitlocker_status=bl_status,
            used_gb=used_gb,
            free_gb=free_gb,
            usage_percent=usage_pct,
            created_date=created_time
        ))
        
    return containers

def create_container(name: str, size_gb: int, dynamic: bool = True, auto_mount: bool = True, 
                     password: Optional[str] = None) -> str:
    """Creates a new VHDX, formats it NTFS, and optionally enables BitLocker with password."""
    ensure_storage_dir()
    s_dir = get_storage_dir()
    if not name.lower().endswith(".vhdx"):
        name += ".vhdx"
        
    path = os.path.join(s_dir, name)
    if os.path.exists(path):
        raise FileExistsError(f"Container '{name}' already exists.")
        
    vhd_type = 'expandable' if dynamic else 'fixed'
    size_mb = int(size_gb) * 1024
    label = name.replace(".vhdx", "")[:11] # NTFS volume label limit
    
    logging.info(f"Creating VHDX via diskpart at {path}")
    commands = f'''
create vdisk file="{path}" maximum={size_mb} type={vhd_type}
select vdisk file="{path}"
attach vdisk
create partition primary
format fs=ntfs quick label="{label}"
assign
'''
    run_diskpart(commands)
    
    # Wait briefly for Windows to register volume
    time.sleep(1.5)
    
    # Check assigned drive letter
    is_mounted, drive_letter = _get_vhd_info(path)
    
    if password and drive_letter:
        logging.info(f"Encrypting new volume {drive_letter} with BitLocker...")
        bitlocker.enable_bitlocker(drive_letter, password)
        
    if not auto_mount:
        dismount_container(path)
        
    return path

def mount_container(path: str):
    """Mounts an existing VHDX container."""
    logging.info(f"Mounting {path}")
    run_diskpart(f'select vdisk file="{path}"\nattach vdisk\n')

def dismount_container(path: str):
    """Safely dismounts a VHDX container, locking BitLocker if active."""
    logging.info(f"Dismounting {path}")
    is_mounted, drive_letter = _get_vhd_info(path)
    if is_mounted and drive_letter:
        try:
            bitlocker.lock_volume(drive_letter)
        except Exception:
            pass
    run_diskpart(f'select vdisk file="{path}"\ndetach vdisk\n')

def panic_dismount_all() -> int:
    """Emergency protocol: Force dismounts and locks ALL mounted VHDX containers."""
    containers = list_containers()
    dismounted_count = 0
    for c in containers:
        if c.is_mounted:
            try:
                dismount_container(c.path)
                dismounted_count += 1
            except Exception as e:
                logging.error(f"Panic dismount failed for {c.name}: {e}")
    return dismounted_count

def delete_container(path: str):
    """Deletes the VHDX file, ensuring it's unmounted first."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Container file not found: {path}")
        
    is_mounted, _ = _get_vhd_info(path)
    if is_mounted:
        raise PermissionError("Cannot delete an active container. Please dismount first.")
        
    os.remove(path)
    # Also clean up any associated checksum files in same dir
    sha_path = f"{path}.sha256"
    if os.path.exists(sha_path):
        os.remove(sha_path)
    logging.info(f"Deleted container {path}")
