"""
Universal Printer Unified Driver Helper
Handles driverless profiles (IPP Everywhere, Mopria, AirPrint), OEM INF parsing, and generic fallback drivers.
"""
import os
import re
from typing import Dict, List, Optional
from pydantic import BaseModel


class DriverProfile(BaseModel):
    name: str
    category: str
    emulation: str # PostScript, PCL6, PWG-Raster, ESC/POS, IPP-Everywhere
    description: str
    supported_os: List[str]


class DriverRegistry:
    """Built-in universal fallback driver catalog."""

    UNIVERSAL_DRIVERS = [
        DriverProfile(
            name="IPP Everywhere (Driverless Standard)",
            category="Driverless",
            emulation="PWG-Raster / PDF",
            description="Modern universal standard for network & WiFi printers (Mopria & AirPrint compatible).",
            supported_os=["windows", "linux", "darwin"]
        ),
        DriverProfile(
            name="Generic PostScript Level 3",
            category="Generic",
            emulation="PostScript",
            description="Universal PostScript driver for enterprise laser/office printers.",
            supported_os=["windows", "linux", "darwin"]
        ),
        DriverProfile(
            name="Generic PCL6 / PCL5e",
            category="Generic",
            emulation="PCL6",
            description="Standard HP PCL printer control language for mono/color lasers.",
            supported_os=["windows", "linux", "darwin"]
        ),
        DriverProfile(
            name="Generic ESC/POS Thermal Receipt",
            category="POS / Thermal",
            emulation="ESC/POS",
            description="Direct thermal receipt printer command set (58mm / 80mm).",
            supported_os=["windows", "linux", "darwin"]
        ),
        DriverProfile(
            name="Generic Text / Raw",
            category="Generic",
            emulation="Raw",
            description="Pass-through raw byte output directly to hardware.",
            supported_os=["windows", "linux", "darwin"]
        ),
    ]

    @classmethod
    def list_universal_profiles(cls) -> List[DriverProfile]:
        return cls.UNIVERSAL_DRIVERS

    @classmethod
    def parse_inf_file(cls, inf_path: str) -> Dict[str, List[str]]:
        """Parses a Windows OEM .INF file to extract supported printer models."""
        if not os.path.exists(inf_path):
            raise FileNotFoundError(f"INF file not found: {inf_path}")

        models = []
        with open(inf_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for [Manufacturer] or [Strings] sections
        for line in content.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith(";"):
                parts = line.split("=", 1)
                left = parts[0].strip()
                right = parts[1].strip().strip('"')
                if any(k in left.lower() for k in ("printer", "device", "model")):
                    models.append(right)

        return {"file": inf_path, "detected_models": models}
