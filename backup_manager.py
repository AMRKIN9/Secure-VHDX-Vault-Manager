import os
import shutil
import hashlib
import json
import time
import re
from typing import List, Dict, Optional, Callable
import logging
from powershell import run_ps

DEFAULT_BACKUP_DIR = os.path.join(os.environ.get("USERPROFILE", "."), "SecureContainers", "Backups")

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

class BackupManager:
    """Handles snapshot backups, SHA-256 checksum verification, rollbacks, and integrity checks."""
    
    @staticmethod
    def calculate_sha256(file_path: str, progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """Calculates SHA-256 hash using streaming chunks to support large VHDX files."""
        hasher = hashlib.sha256()
        total_size = os.path.getsize(file_path)
        processed = 0
        chunk_size = 4 * 1024 * 1024  # 4 MB chunks
        
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                processed += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(processed / total_size)
                    
        return hasher.hexdigest()

    @classmethod
    def create_backup(cls, vhdx_path: str, target_dir: Optional[str] = None, 
                      progress_callback: Optional[Callable[[str], None]] = None) -> Dict:
        """Creates an authenticated snapshot of a VHDX file with a .sha256 checksum file."""
        if not os.path.exists(vhdx_path):
            raise FileNotFoundError(f"Source vault not found: {vhdx_path}")

        dest_dir = target_dir or DEFAULT_BACKUP_DIR
        ensure_dir(dest_dir)

        base_name = os.path.basename(vhdx_path)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name_part, ext = os.path.splitext(base_name)
        backup_filename = f"{name_part}_backup_{timestamp}{ext}"
        backup_path = os.path.join(dest_dir, backup_filename)
        sha_path = f"{backup_path}.sha256"

        if progress_callback:
            progress_callback("Copying vault binary to backup storage...")

        # Copy the VHDX binary
        shutil.copy2(vhdx_path, backup_path)

        if progress_callback:
            progress_callback("Calculating cryptographic SHA-256 integrity seal...")

        checksum = cls.calculate_sha256(backup_path)

        # Write checksum file
        with open(sha_path, "w", encoding="utf-8") as f:
            f.write(f"{checksum} *{backup_filename}\n")

        size_gb = round(os.path.getsize(backup_path) / (1024**3), 2)
        meta = {
            "source": vhdx_path,
            "backup_name": backup_filename,
            "backup_path": backup_path,
            "checksum": checksum,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size_gb": size_gb
        }

        # Append to manifest in dest_dir
        manifest_path = os.path.join(dest_dir, "manifest.json")
        manifest = []
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest = json.load(mf)
            except Exception:
                manifest = []
        manifest.insert(0, meta)
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        return meta

    @classmethod
    def verify_backup(cls, backup_path: str, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Verifies a backup file against its saved .sha256 file."""
        sha_path = f"{backup_path}.sha256"
        if not os.path.exists(sha_path):
            return False

        with open(sha_path, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            expected_hash = line.split()[0] if line else ""

        current_hash = cls.calculate_sha256(backup_path, progress_callback)
        return expected_hash.lower() == current_hash.lower()

    @classmethod
    def restore_backup(cls, backup_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        """Rolls back and restores a backup over the active VHDX vault, verifying SHA-256 first."""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        if progress_callback:
            progress_callback("Verifying SHA-256 checksum before rollback...")

        if not cls.verify_backup(backup_path):
            raise ValueError("Integrity check failed: Backup SHA-256 seal mismatch.")

        base_name = os.path.basename(backup_path)
        match = re.match(r"^(.*?)_backup_\d{8}_\d{6}\.vhdx$", base_name, re.IGNORECASE)
        if match:
            target_name = match.group(1) + ".vhdx"
        else:
            target_name = base_name.replace("_backup", "")

        from vhd_manager import get_storage_dir, _get_vhd_info, dismount_container
        target_path = os.path.join(get_storage_dir(), target_name)

        if os.path.exists(target_path):
            is_mounted, _ = _get_vhd_info(target_path)
            if is_mounted:
                if progress_callback:
                    progress_callback(f"Dismounting active vault {target_name}...")
                dismount_container(target_path)

        if progress_callback:
            progress_callback(f"Restoring {target_name} from backup image...")

        shutil.copy2(backup_path, target_path)
        return target_path

    @classmethod
    def delete_backup(cls, backup_path: str):
        """Deletes a backup file, its .sha256 seal, and updates the manifest."""
        if os.path.exists(backup_path):
            os.remove(backup_path)
        sha_path = f"{backup_path}.sha256"
        if os.path.exists(sha_path):
            os.remove(sha_path)

        dest_dir = os.path.dirname(backup_path)
        manifest_path = os.path.join(dest_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest = json.load(mf)
                manifest = [b for b in manifest if os.path.abspath(b.get("backup_path", "")) != os.path.abspath(backup_path)]
                with open(manifest_path, "w", encoding="utf-8") as mf:
                    json.dump(manifest, mf, indent=2)
            except Exception as e:
                logging.error(f"Failed to update manifest after deletion: {e}")

    @classmethod
    def list_backups(cls, target_dir: Optional[str] = None) -> List[Dict]:
        """Lists all existing backups with metadata and verification status."""
        dest_dir = target_dir or DEFAULT_BACKUP_DIR
        manifest_path = os.path.join(dest_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest = json.load(mf)
                    return [b for b in manifest if os.path.exists(b.get("backup_path", ""))]
            except Exception as e:
                logging.error(f"Failed to read backup manifest: {e}")
        return []

    @staticmethod
    def run_disk_diagnostic(drive_letter: str) -> str:
        """Runs chkdsk read-only diagnostic on a mounted drive letter."""
        clean_letter = drive_letter.replace(":", "").strip()
        ps_script = f"chkdsk {clean_letter}:"
        try:
            res = run_ps(ps_script, check=False)
            return res.stdout or res.stderr or "Diagnostic finished with no output."
        except Exception as e:
            return f"Diagnostic failed: {e}"
