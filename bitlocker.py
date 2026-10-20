import os
import logging
from powershell import run_ps, run_ps_json

def get_volume_status(drive_letter: str) -> str:
    """Returns 'Off', 'Locked', 'Unlocked', or 'Unknown'."""
    try:
        clean_letter = drive_letter.replace(":", "").strip() + ":"
        script = f"Get-BitLockerVolume -MountPoint '{clean_letter}' | Select-Object ProtectionStatus, VolumeStatus, LockStatus"
        data = run_ps_json(script, check=False)
        
        if not data:
            return "Off"
            
        protection_status = data.get("ProtectionStatus", 0)
        lock_status = data.get("LockStatus", 0)
        
        if protection_status == 0:
            return "Off"
        elif lock_status == 1:
            return "Locked"
        elif lock_status == 0:
            return "Unlocked"
            
        return "Unknown"
    except Exception as e:
        logging.error(f"Error checking BitLocker status for {drive_letter}: {e}")
        return "Unknown"

def enable_bitlocker(drive_letter: str, password: str) -> str:
    """Enables BitLocker XTS-AES 256 on the drive using the provided password."""
    clean_letter = drive_letter.replace(":", "").strip() + ":"
    # Escape single quotes in password for PowerShell string literal safety
    escaped_pwd = password.replace("'", "''")
    
    script = f"""
    $sec = ConvertTo-SecureString '{escaped_pwd}' -AsPlainText -Force
    Enable-BitLocker -MountPoint '{clean_letter}' -EncryptionMethod XtsAes256 -UsedSpaceOnly -PasswordProtector -Secret $sec
    """
    res = run_ps(script, check=True)
    return res.stdout

def unlock_volume_password(drive_letter: str, password: str) -> bool:
    """Unlocks a locked BitLocker volume using a password."""
    clean_letter = drive_letter.replace(":", "").strip() + ":"
    escaped_pwd = password.replace("'", "''")
    script = f"""
    $sec = ConvertTo-SecureString '{escaped_pwd}' -AsPlainText -Force
    Unlock-BitLocker -MountPoint '{clean_letter}' -Password $sec
    """
    try:
        run_ps(script, check=True)
        return True
    except Exception as e:
        logging.error(f"Failed to unlock {drive_letter}: {e}")
        raise

def lock_volume(drive_letter: str):
    """Locks a BitLocker volume and dismounts it if forced."""
    clean_letter = drive_letter.replace(":", "").strip() + ":"
    try:
        script = f"Lock-BitLocker -MountPoint '{clean_letter}' -ForceDismount"
        run_ps(script, check=True)
    except Exception as e:
        logging.error(f"Error locking BitLocker volume {drive_letter}: {e}")
        raise

def unlock_volume_native(drive_letter: str):
    """Triggers the Windows native BitLocker unlock dialog."""
    try:
        os.startfile(drive_letter)
    except Exception as e:
        logging.error(f"Error opening drive for unlock {drive_letter}: {e}")

def open_bitlocker_setup():
    """Opens the Windows Control Panel BitLocker applet."""
    try:
        run_ps("control /name Microsoft.BitLockerDriveEncryption", check=False)
    except Exception as e:
        logging.error(f"Error opening BitLocker setup: {e}")
