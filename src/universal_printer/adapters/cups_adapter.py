"""
Universal Printer CUPS Adapter (Linux & macOS)
Interacts with CUPS daemon via lpadmin, lpstat, lpinfo, and lp CLI utilities.
"""
import subprocess
import shutil
import uuid
import os
from typing import List, Optional

from universal_printer.adapters.base import BasePrinterAdapter
from universal_printer.core.models import (
    PrinterDevice, 
    ConnectionType, 
    PrinterStatus, 
    PrintJob, 
    PrintJobOptions
)


class CupsAdapter(BasePrinterAdapter):
    """CUPS management for Linux and macOS environments."""

    def __init__(self):
        self.has_cups = shutil.which("lpadmin") is not None

    def _exec(self, cmd_list: List[str]) -> Tuple[int, str, str]:
        """Runs a system command safely."""
        try:
            res = subprocess.run(cmd_list, capture_output=True, text=True)
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return -1, "", str(e)

    def list_installed_printers(self) -> List[PrinterDevice]:
        """Lists installed CUPS printers via lpstat -p -d -v."""
        if not self.has_cups:
            return []

        _, out, _ = self._exec(["lpstat", "-v"])
        printers = []
        for line in out.splitlines():
            # "device for EPSON_L3150: ipp://192.168.1.50:631/ipp/print"
            if line.startswith("device for "):
                parts = line[len("device for "):].split(":")
                if len(parts) >= 2:
                    p_name = parts[0].strip()
                    device_uri = ":".join(parts[1:]).strip()

                    conn_type = ConnectionType.IPP if "ipp" in device_uri else ConnectionType.SOCKET

                    dev = PrinterDevice(
                        id=f"cups-{p_name}",
                        name=p_name,
                        make_and_model=p_name,
                        connection_type=conn_type,
                        uri=device_uri,
                        is_installed=True,
                        status=PrinterStatus.IDLE
                    )
                    printers.append(dev)
        return printers

    def list_available_drivers(self) -> List[str]:
        """Lists available PPD models and IPP Everywhere drivers via lpinfo -m."""
        if not self.has_cups:
            return ["everywhere", "raw"]
        _, out, _ = self._exec(["lpinfo", "-m"])
        drivers = []
        for line in out.splitlines()[:50]: # Top 50 common drivers
            if line.strip():
                drivers.append(line.strip())
        return drivers

    def install_printer(self, device: PrinterDevice, driver_name: Optional[str] = None) -> bool:
        """
        Installs a printer in CUPS using driverless `everywhere` or specified PPD:
        lpadmin -p <name> -E -v <uri> -m everywhere
        """
        if not self.has_cups:
            return False

        # Use driverless IPP Everywhere as default
        model = driver_name or "everywhere"
        cmd = ["lpadmin", "-p", device.name, "-E", "-v", device.uri, "-m", model]
        code, out, err = self._exec(cmd)
        
        # Fallback to raw if everywhere fails
        if code != 0:
            cmd_fallback = ["lpadmin", "-p", device.name, "-E", "-v", device.uri, "-m", "raw"]
            code, _, _ = self._exec(cmd_fallback)

        # Enable accepting jobs
        self._exec(["cupsaccept", device.name])
        self._exec(["cupsenable", device.name])
        return code == 0

    def remove_printer(self, printer_name: str) -> bool:
        """Removes a printer queue via lpadmin -x."""
        if not self.has_cups:
            return False
        code, _, _ = self._exec(["lpadmin", "-x", printer_name])
        return code == 0

    def set_default_printer(self, printer_name: str) -> bool:
        """Sets default printer via lpoptions -d."""
        if not self.has_cups:
            return False
        code, _, _ = self._exec(["lpoptions", "-d", printer_name])
        return code == 0

    def print_file(self, printer_name: str, file_path: str, options: Optional[PrintJobOptions] = None) -> PrintJob:
        """Submits a print job via lp command."""
        opts = options or PrintJobOptions()
        job_id = f"job-{uuid.uuid4().hex[:8]}"

        cmd = ["lp", "-d", printer_name, "-n", str(opts.copies)]
        if opts.duplex:
            cmd.extend(["-o", "sides=two-sided-long-edge"])
        if opts.orientation:
            cmd.extend(["-o", f"orientation-requested={3 if 'portrait' in opts.orientation else 4}"])

        cmd.append(file_path)
        self._exec(cmd)

        return PrintJob(
            job_id=job_id,
            printer_id=printer_name,
            file_path=file_path,
            options=opts,
            status="sent_to_cups"
        )
