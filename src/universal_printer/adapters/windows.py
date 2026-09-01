"""
Universal Printer Windows Adapter
Manages Windows Print Spooler, Win32 printing, PowerShell PrintManagement, and INF/PPD driver installation.
"""
import subprocess
import json
import uuid
import os
from typing import List, Optional

from universal_printer.adapters.base import BasePrinterAdapter
from universal_printer.core.models import (
    PrinterDevice, 
    ConnectionType, 
    PrinterStatus, 
    PrinterCapabilities, 
    PrintJob, 
    PrintJobOptions
)


class WindowsAdapter(BasePrinterAdapter):
    """Native Windows Spooler and Driver Management."""

    def __init__(self):
        pass

    def _run_ps(self, cmd: str) -> str:
        """Executes a PowerShell command and returns output."""
        full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd]
        res = subprocess.run(full_cmd, capture_output=True, text=True)
        if res.returncode != 0 and res.stderr:
            # Return stderr if failed
            return res.stderr.strip()
        return res.stdout.strip()

    def list_installed_printers(self) -> List[PrinterDevice]:
        """Lists all Windows printers using PowerShell Get-Printer."""
        ps_cmd = (
            "Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus, Shared, Type | "
            "ConvertTo-Json -Compress"
        )
        output = self._run_ps(ps_cmd)
        if not output:
            return []

        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
        except Exception:
            return []

        printers = []
        for item in data:
            name = item.get("Name", "Unknown")
            driver = item.get("DriverName", "Generic")
            port = item.get("PortName", "")

            conn_type = ConnectionType.LOCAL_SPOOLER
            if "ipp" in port.lower() or "http" in port.lower():
                conn_type = ConnectionType.IPP
            elif "9100" in port or "." in port:
                conn_type = ConnectionType.SOCKET
            elif "usb" in port.lower():
                conn_type = ConnectionType.USB

            dev = PrinterDevice(
                id=f"win-{name.replace(' ', '_')}",
                name=name,
                make_and_model=driver,
                connection_type=conn_type,
                uri=f"winspool://{name}",
                is_installed=True,
                status=PrinterStatus.IDLE,
                raw_info=item
            )
            printers.append(dev)

        return printers

    def list_available_drivers(self) -> List[str]:
        """Queries all drivers registered in the Windows Driver Store."""
        ps_cmd = "Get-PrinterDriver | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
        output = self._run_ps(ps_cmd)
        if not output:
            return []
        try:
            res = json.loads(output)
            return res if isinstance(res, list) else [res]
        except Exception:
            return [line.strip() for line in output.splitlines() if line.strip()]

    def install_printer(self, device: PrinterDevice, driver_name: Optional[str] = None) -> bool:
        """
        Installs a printer on Windows:
        1. Creates/Verifies the Port (Standard TCP/IP, IPP, or WSD).
        2. Assigns Driver (Generic / Postscript / IPP Class Driver / Custom).
        3. Invokes Add-Printer.
        """
        # Determine fallback driver if not specified
        if not driver_name:
            avail = self.list_available_drivers()
            # Prioritize clean universal drivers
            preferred = [
                "Microsoft IPP Class Driver",
                "Microsoft Print to PDF",
                "Generic / Text Only",
                "Microsoft PS Class Driver",
                "Generic Postscript Printer"
            ]
            for pref in preferred:
                if any(pref.lower() in d.lower() for d in avail):
                    driver_name = next(d for d in avail if pref.lower() in d.lower())
                    break
            if not driver_name and avail:
                driver_name = avail[0]

        driver_name = driver_name or "Generic / Text Only"
        port_name = f"Port_{device.id}"

        # If IP address is present, create TCP/IP or IPP port
        if device.address:
            create_port_cmd = f"""
            $port = Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue
            if (-not $port) {{
                Add-PrinterPort -Name '{port_name}' -PrinterHostAddress '{device.address}'
            }}
            """
            self._run_ps(create_port_cmd)
        else:
            port_name = "LPT1:"

        add_printer_cmd = f"""
        $existing = Get-Printer -Name '{device.name}' -ErrorAction SilentlyContinue
        if ($existing) {{
            Set-Printer -Name '{device.name}' -DriverName '{driver_name}' -PortName '{port_name}'
        }} else {{
            Add-Printer -Name '{device.name}' -DriverName '{driver_name}' -PortName '{port_name}'
        }}
        """
        out = self._run_ps(add_printer_cmd)
        return "Error" not in out

    def install_inf_driver(self, inf_path: str, driver_name: str) -> bool:
        """Installs a driver from an OEM INF package using pnputil / rundll32."""
        if not os.path.exists(inf_path):
            raise FileNotFoundError(f"INF file not found: {inf_path}")

        # Stage driver via pnputil
        pnp_cmd = f"pnputil /add-driver '{inf_path}' /install"
        subprocess.run(["powershell", "-Command", pnp_cmd], capture_output=True)

        # Register in Spooler
        ps_cmd = f"Add-PrinterDriver -Name '{driver_name}'"
        out = self._run_ps(ps_cmd)
        return "Error" not in out

    def remove_printer(self, printer_name: str) -> bool:
        """Removes an installed printer from Windows Spooler."""
        cmd = f"Remove-Printer -Name '{printer_name}' -ErrorAction SilentlyContinue"
        self._run_ps(cmd)
        return True

    def set_default_printer(self, printer_name: str) -> bool:
        """Sets default Windows printer."""
        cmd = f"(New-Object -ComObject WScript.Network).SetDefaultPrinter('{printer_name}')"
        self._run_ps(cmd)
        return True

    def print_file(self, printer_name: str, file_path: str, options: Optional[PrintJobOptions] = None) -> PrintJob:
        """Prints a file directly through Windows Shell / Print Spooler."""
        opts = options or PrintJobOptions()
        job_id = f"job-{uuid.uuid4().hex[:8]}"

        abs_path = os.path.abspath(file_path)
        # PowerShell Out-Printer or Start-Process -Verb PrintTo
        ps_cmd = f"""
        Start-Process -FilePath '{abs_path}' -Verb PrintTo -ArgumentList '"{printer_name}"' -PassThru | Out-Null
        """
        self._run_ps(ps_cmd)

        return PrintJob(
            job_id=job_id,
            printer_id=printer_name,
            file_path=abs_path,
            options=opts,
            status="sent_to_spooler"
        )
