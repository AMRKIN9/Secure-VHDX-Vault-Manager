from dataclasses import dataclass
from typing import Optional

@dataclass
class Container:
    name: str
    path: str
    size_gb: float
    is_mounted: bool
    drive_letter: Optional[str] = None
    bitlocker_status: str = "Off"  # "Off", "Locked", "Unlocked", "Unknown"
    used_gb: Optional[float] = None
    free_gb: Optional[float] = None
    usage_percent: Optional[float] = None
    created_date: Optional[str] = None
