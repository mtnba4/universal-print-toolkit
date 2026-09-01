"""
Universal Printer Core Models
Data structures for discovered printers, print jobs, and device capabilities.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ConnectionType(str, Enum):
    IPP = "ipp"
    IPPS = "ipps"
    SOCKET = "socket"  # Raw Port 9100 / JetDirect
    LPD = "lpd"
    WSD = "wsd"
    USB = "usb"
    LOCAL_SPOOLER = "local_spooler"
    VIRTUAL = "virtual"


class PrinterStatus(str, Enum):
    IDLE = "idle"
    PRINTING = "printing"
    STOPPED = "stopped"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class PageOrientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    REVERSE_PORTRAIT = "reverse_portrait"
    REVERSE_LANDSCAPE = "reverse_landscape"


class ColorMode(str, Enum):
    MONOCHROME = "monochrome"
    COLOR = "color"
    GRAYSCALE = "grayscale"


class PrinterCapabilities(BaseModel):
    supports_color: bool = False
    supports_duplex: bool = False
    supported_media: List[str] = Field(default_factory=lambda: ["A4", "Letter"])
    supported_formats: List[str] = Field(default_factory=lambda: [
        "application/pdf", 
        "application/postscript", 
        "image/pwg-raster", 
        "application/octet-stream"
    ])
    max_resolution_dpi: int = 600
    is_driverless: bool = True  # IPP Everywhere / AirPrint / Mopria standard


class PrinterDevice(BaseModel):
    id: str
    name: str
    make_and_model: str = "Generic Printer"
    connection_type: ConnectionType = ConnectionType.IPP
    address: Optional[str] = None  # IP or hostname
    port: Optional[int] = None     # 631 (IPP), 9100 (Socket), etc.
    uri: str                       # e.g., ipp://192.168.1.100:631/ipp/print
    location: Optional[str] = None
    status: PrinterStatus = PrinterStatus.IDLE
    is_installed: bool = False
    is_default: bool = False
    capabilities: PrinterCapabilities = Field(default_factory=PrinterCapabilities)
    raw_info: Dict[str, Any] = Field(default_factory=dict)


class PrintJobOptions(BaseModel):
    copies: int = 1
    color_mode: ColorMode = ColorMode.MONOCHROME
    orientation: PageOrientation = PageOrientation.PORTRAIT
    duplex: bool = False
    media: str = "A4"
    fit_to_page: bool = True
    page_ranges: Optional[str] = None
    job_name: str = "Universal Print Job"


class PrintJob(BaseModel):
    job_id: str
    printer_id: str
    file_path: str
    options: PrintJobOptions = Field(default_factory=PrintJobOptions)
    status: str = "queued"
    bytes_sent: int = 0
    total_bytes: int = 0
