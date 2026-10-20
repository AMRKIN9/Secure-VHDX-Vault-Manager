import os
import logging
from powershell import run_ps, run_ps_json

def get_volume_status(drive_letter: str) -> str:
    """Returns 'Off', 'Locked', 'Unlocked', or 'Unknown'."""
    try:
        # Get-BitLockerVolume requires Admin rights
        # Format of ProtectionStatus: 0: Off, 1: On, 2: Unknown
        # Format of VolumeStatus: 0: FullyDecrypted, 1: FullyEncrypted, 2: EncryptionInProgress, 3: DecryptionInProgress, 4: EncryptionSuspended, 5: DecryptionSuspended
        # LockStatus: 0: Unlocked, 1: Locked
        
        script = f"Get-BitLockerVolume -MountPoint '{drive_letter}' | Select-Object ProtectionStatus, VolumeStatus, LockStatus"
        data = run_ps_json(script, check=False)
        
        if not data:
            return "Off" # If we can't get it, it might not be a BitLocker volume or no admin rights. Let's assume Off if no data or not found.
            
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

def lock_volume(drive_letter: str):
    """Locks a BitLocker volume and dismounts it if forced."""
    try:
        # We use ForceDismount to ensure it locks even if in use
        script = f"Lock-BitLocker -MountPoint '{drive_letter}' -ForceDismount"
        run_ps(script)
    except Exception as e:
        logging.error(f"Error locking BitLocker volume {drive_letter}: {e}")
        raise

def unlock_volume(drive_letter: str):
    """Opens the Windows native BitLocker unlock dialog."""
    # The native way to prompt for unlock is to try and open the drive or use the bdeui.exe
    # Alternatively, just launching explorer on the drive will prompt the user
    try:
        # This will open Explorer. If it's locked, Windows will naturally prompt for the password.
        os.startfile(drive_letter)
    except Exception as e:
        logging.error(f"Error opening drive for unlock {drive_letter}: {e}")

def open_bitlocker_setup():
    """Opens the Windows Control Panel BitLocker applet."""
    try:
        # control /name Microsoft.BitLockerDriveEncryption
        run_ps("control /name Microsoft.BitLockerDriveEncryption", check=False)
    except Exception as e:
        logging.error(f"Error opening BitLocker setup: {e}")
