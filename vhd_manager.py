import os
import glob
from typing import List, Optional
from models import Container
from powershell import run_ps
import bitlocker
import logging
import subprocess
import re

STORAGE_DIR = os.path.join(os.environ["USERPROFILE"], "SecureContainers")

def ensure_storage_dir():
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)

def run_diskpart(commands: str) -> str:
    """Runs diskpart securely via subprocess."""
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

def _get_vhd_info(path: str):
    """Returns a tuple (is_mounted: bool, drive_letter: str|None)."""
    out = run_diskpart(f'select vdisk file="{path}"\ndetail vdisk\n')
    
    # Check if an associated disk is found
    match = re.search(r"Associated disk#:\s*(\d+)", out)
    if not match:
        return False, None
        
    disk_num = match.group(1)
    
    # Query the disk details to find the assigned volume letter
    out_disk = run_diskpart(f'select disk {disk_num}\ndetail disk\n')
    
    for line in out_disk.splitlines():
        line = line.strip()
        if line.startswith("Volume"):
            parts = line.split()
            # Diskpart typically outputs: Volume ###  Ltr  Label  Fs  Type  Size  Status  Info
            if len(parts) >= 3:
                # The drive letter is always a single alphabetical character
                if len(parts[2]) == 1 and parts[2].isalpha():
                    return True, parts[2].upper() + ":"
                if len(parts[3]) == 1 and parts[3].isalpha():
                     return True, parts[3].upper() + ":"
                     
    return True, None

def list_containers() -> List[Container]:
    """Scans the storage directory and returns a list of Container objects."""
    ensure_storage_dir()
    containers = []
    
    for vhdx_file in glob.glob(os.path.join(STORAGE_DIR, "*.vhdx")):
        name = os.path.basename(vhdx_file)
        size_gb = round(os.path.getsize(vhdx_file) / (1024**3), 2)
        
        is_mounted, drive_letter = _get_vhd_info(vhdx_file)
        bl_status = "Off"
        
        if is_mounted and drive_letter:
            bl_status = bitlocker.get_volume_status(drive_letter)
                
        containers.append(Container(
            name=name,
            path=vhdx_file,
            size_gb=size_gb,
            is_mounted=is_mounted,
            drive_letter=drive_letter,
            bitlocker_status=bl_status
        ))
        
    return containers

def create_container(name: str, size_gb: int, dynamic: bool = True, auto_mount: bool = True):
    """Creates a new VHDX, initializes it, partitions, and formats using diskpart."""
    ensure_storage_dir()
    if not name.lower().endswith(".vhdx"):
        name += ".vhdx"
        
    path = os.path.join(STORAGE_DIR, name)
    if os.path.exists(path):
        raise FileExistsError(f"Container '{name}' already exists.")
        
    vhd_type = 'expandable' if dynamic else 'fixed'
    size_mb = int(size_gb) * 1024
    
    logging.info(f"Creating VHDX via diskpart at {path}")
    commands = f'''
create vdisk file="{path}" maximum={size_mb} type={vhd_type}
select vdisk file="{path}"
attach vdisk
create partition primary
format fs=ntfs quick label="SecureVault"
assign
'''
    if not auto_mount:
        commands += "\ndetach vdisk\n"
        
    run_diskpart(commands)

def mount_container(path: str):
    """Mounts an existing VHDX container."""
    logging.info(f"Mounting {path}")
    run_diskpart(f'select vdisk file="{path}"\nattach vdisk\n')

def dismount_container(path: str):
    """Safely dismounts a VHDX container."""
    logging.info(f"Dismounting {path}")
    run_diskpart(f'select vdisk file="{path}"\ndetach vdisk\n')

def delete_container(path: str):
    """Deletes the VHDX file, ensuring it's unmounted first."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Container file not found: {path}")
        
    is_mounted, _ = _get_vhd_info(path)
    if is_mounted:
        raise PermissionError("Cannot delete a mounted container. Please dismount first.")
        
    os.remove(path)
    logging.info(f"Deleted {path}")
