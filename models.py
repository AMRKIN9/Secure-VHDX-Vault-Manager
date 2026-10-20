from dataclasses import dataclass
from typing import Optional

@dataclass
class Container:
    name: str
    path: str
    size_gb: float
    is_mounted: bool
    drive_letter: Optional[str] = None
    bitlocker_status: str = "Unknown"  # "Off", "Locked", "Unlocked", "Unknown"
