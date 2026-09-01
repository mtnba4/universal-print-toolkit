"""
Universal Printer Unified Manager
Main cross-platform interface orchestrating discovery, adapter selection, pipeline, and printing.
"""
import sys
import os
import socket
from typing import List, Optional, Tuple

from universal_printer.core.models import (
    PrinterDevice, 
    ConnectionType, 
    PrintJobOptions, 
    PrintJob
)
from universal_printer.core.discovery import PrinterDiscovery
from universal_printer.core.pipeline import DocumentPipeline
from universal_printer.core.ipp_client import IPPClient
from universal_printer.adapters.base import BasePrinterAdapter
from universal_printer.adapters.windows import WindowsAdapter
from universal_printer.adapters.cups_adapter import CupsAdapter


class UniversalPrinterManager:
    """Unified Facade for all OS printer operations."""

    def __init__(self):
        self.os_type = sys.platform # 'win32', 'linux', 'darwin'
        if self.os_type == "win32":
            self.adapter: BasePrinterAdapter = WindowsAdapter()
        else:
            self.adapter: BasePrinterAdapter = CupsAdapter()

    def scan_printers(self, timeout: float = 3.0) -> List[PrinterDevice]:
        """Discovers network printers via IPP mDNS/Bonjour."""
        return PrinterDiscovery.discover_all(timeout=timeout)

    def list_installed_printers(self) -> List[PrinterDevice]:
        """Lists printers installed on the host OS."""
        return self.adapter.list_installed_printers()

    def list_available_drivers(self) -> List[str]:
        """Lists drivers available in the OS driver store."""
        return self.adapter.list_available_drivers()

    def install_printer(self, name: str, uri_or_ip: str, driver_name: Optional[str] = None) -> bool:
        """Installs any printer using its IPP URI, IP Address, or standard driver."""
        # Normalize connection
        if "://" in uri_or_ip:
            uri = uri_or_ip
            proto = uri.split("://")[0]
            host = uri.split("://")[1].split("/")[0].split(":")[0]
            conn_type = ConnectionType.IPP if "ipp" in proto else ConnectionType.SOCKET
        else:
            host = uri_or_ip
            uri = f"ipp://{host}:631/ipp/print"
            conn_type = ConnectionType.IPP

        dev = PrinterDevice(
            id=f"dev-{name.replace(' ', '_')}",
            name=name,
            address=host,
            uri=uri,
            connection_type=conn_type
        )
        return self.adapter.install_printer(dev, driver_name=driver_name)

    def remove_printer(self, name: str) -> bool:
        """Removes a printer from the OS."""
        return self.adapter.remove_printer(name)

    def set_default_printer(self, name: str) -> bool:
        """Sets default OS printer."""
        return self.adapter.set_default_printer(name)

    def print_file(self, printer_target: str, file_path: str, options: Optional[PrintJobOptions] = None, direct_network: bool = False) -> PrintJob:
        """
        Unified print function:
        1. If direct_network is True or target is an IP / ipp:// URI, sends directly via IPP or Socket without OS driver.
        2. Otherwise, prints via OS Print Spooler (CUPS or Windows Spooler).
        """
        opts = options or PrintJobOptions()

        # Check if direct IPP / Network socket printing requested
        if direct_network or printer_target.startswith("ipp://") or printer_target.startswith("ipps://"):
            uri = printer_target if "://" in printer_target else f"ipp://{printer_target}:631/ipp/print"
            client = IPPClient(uri)
            # Convert document to printable PDF / Raster
            data, mime = DocumentPipeline.prepare_document(file_path, opts, target_format="application/pdf")
            job_num = client.print_file(data, mime_type=mime, options=opts)
            return PrintJob(
                job_id=f"ipp-{job_num}",
                printer_id=printer_target,
                file_path=file_path,
                options=opts,
                status="sent_direct_ipp",
                bytes_sent=len(data),
                total_bytes=len(data)
            )
        
        elif printer_target.startswith("socket://"):
            # Raw Port 9100 Direct Socket print
            host = printer_target.replace("socket://", "").split(":")[0]
            port = 9100
            data, _ = DocumentPipeline.prepare_document(file_path, opts, target_format="application/octet-stream")
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((host, port))
            s.sendall(data)
            s.close()

            return PrintJob(
                job_id="raw-socket-job",
                printer_id=printer_target,
                file_path=file_path,
                options=opts,
                status="sent_direct_socket",
                bytes_sent=len(data),
                total_bytes=len(data)
            )

        # Standard OS Spooler printing
        return self.adapter.print_file(printer_target, file_path, options=opts)
