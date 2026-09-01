"""
Universal Printer Discovery Engine
Discovers network printers via mDNS/Bonjour (AirPrint, IPP, IPPS), Raw JetDirect (Port 9100), and USB Devices.
"""
import socket
import time
from typing import List, Dict, Any, Optional
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

from universal_printer.core.models import PrinterDevice, ConnectionType, PrinterCapabilities, PrinterStatus


class ZeroconfPrinterListener(ServiceListener):
    def __init__(self):
        self.printers: Dict[str, PrinterDevice] = {}

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info:
            return

        # Parse IP addresses
        addresses = info.parsed_addresses()
        ip = addresses[0] if addresses else "127.0.0.1"
        port = info.port

        # Decode properties TXT record
        props = {}
        if info.properties:
            for k, v in info.properties.items():
                try:
                    key = k.decode("utf-8", errors="ignore") if isinstance(k, bytes) else str(k)
                    val = v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else str(v)
                    props[key] = val
                except Exception:
                    pass

        # Determine make and model
        make_and_model = props.get("ty") or props.get("model") or props.get("product") or name.split(".")[0]
        resource_path = props.get("rp", "ipp/print")
        if not resource_path.startswith("/"):
            resource_path = "/" + resource_path

        is_secure = "_ipps._tcp" in type_
        proto = "ipps" if is_secure else "ipp"
        conn_type = ConnectionType.IPPS if is_secure else ConnectionType.IPP
        uri = f"{proto}://{ip}:{port}{resource_path}"

        # Parse capabilities
        pdl = props.get("pdl", "")
        supported_formats = [fmt.strip() for fmt in pdl.split(",") if fmt.strip()]
        if not supported_formats:
            supported_formats = ["application/pdf", "image/pwg-raster", "application/postscript"]

        supports_color = props.get("Color") == "T" or props.get("color") == "T" or "color" in pdl.lower()
        supports_duplex = props.get("Duplex") == "T" or props.get("duplex") == "T"

        caps = PrinterCapabilities(
            supports_color=supports_color,
            supports_duplex=supports_duplex,
            supported_formats=supported_formats,
            is_driverless=True
        )

        clean_name = name.split("._")[0].replace("\\", "")

        printer = PrinterDevice(
            id=f"net-{ip}-{port}",
            name=clean_name,
            make_and_model=make_and_model,
            connection_type=conn_type,
            address=ip,
            port=port,
            uri=uri,
            location=props.get("note") or props.get("adminurl"),
            status=PrinterStatus.IDLE,
            capabilities=caps,
            raw_info=props
        )
        self.printers[printer.id] = printer


class PrinterDiscovery:
    """Orchestrates multi-protocol printer discovery."""

    @staticmethod
    def discover_mdns(timeout_seconds: float = 3.0) -> List[PrinterDevice]:
        """Discovers network printers broadcasting IPP/IPPS via mDNS/Bonjour."""
        zeroconf = Zeroconf()
        listener = ZeroconfPrinterListener()
        
        service_types = [
            "_ipp._tcp.local.",
            "_ipps._tcp.local.",
            "_pdl-datastream._tcp.local.", # JetDirect / Raw Port 9100
            "_printer._tcp.local."         # LPD
        ]
        
        browser = ServiceBrowser(zeroconf, service_types, listener)
        time.sleep(timeout_seconds)
        zeroconf.close()
        return list(listener.printers.values())

    @staticmethod
    def probe_port_9100(subnet_prefix: str, start_ip: int = 1, end_ip: int = 254, timeout: float = 0.2) -> List[PrinterDevice]:
        """Probes standard Raw JetDirect (Port 9100) printers across a subnet."""
        found = []
        for i in range(start_ip, end_ip + 1):
            ip = f"{subnet_prefix}.{i}"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                if s.connect_ex((ip, 9100)) == 0:
                    device = PrinterDevice(
                        id=f"raw-{ip}-9100",
                        name=f"Raw Network Printer ({ip})",
                        make_and_model="Standard JetDirect / Port 9100",
                        connection_type=ConnectionType.SOCKET,
                        address=ip,
                        port=9100,
                        uri=f"socket://{ip}:9100",
                        status=PrinterStatus.IDLE,
                        capabilities=PrinterCapabilities(
                            supported_formats=["application/octet-stream", "application/postscript", "application/vnd.hp-PCL"],
                            is_driverless=False
                        )
                    )
                    found.append(device)
                s.close()
            except Exception:
                continue
        return found

    @classmethod
    def discover_all(cls, timeout: float = 3.0) -> List[PrinterDevice]:
        """Runs comprehensive discovery across available discovery methods."""
        return cls.discover_mdns(timeout_seconds=timeout)
