import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_ps(script: str, check: bool = True) -> subprocess.CompletedProcess:
    """Runs a powershell script and returns the CompletedProcess object."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", script
    ]
    logging.debug(f"Executing PS: {script}")
    # Using CREATE_NO_WINDOW to prevent powershell windows from popping up
    creationflags = 0
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        creationflags = subprocess.CREATE_NO_WINDOW
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        creationflags=creationflags
    )
    if check and result.returncode != 0:
        logging.error(f"PS Command failed: {script}")
        logging.error(f"STDOUT: {result.stdout}")
        logging.error(f"STDERR: {result.stderr}")
        raise RuntimeError(f"PowerShell command failed with code {result.returncode}:\n{result.stderr.strip() or result.stdout.strip()}")
        
    return result

def run_ps_json(script: str, check: bool = True):
    """Runs a powershell script that returns JSON, and parses the output."""
    # Ensure the script outputs JSON
    full_script = f"({script}) | ConvertTo-Json -Compress"
    try:
        result = run_ps(full_script, check=check)
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON output: {e}")
        return None
    except Exception as e:
        if check:
            raise
        return None
