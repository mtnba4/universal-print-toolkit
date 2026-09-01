"""
Universal Printer OS Adapter Interface
Provides standard contracts for managing printers across Windows, Linux, and macOS.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from universal_printer.core.models import PrinterDevice, PrintJobOptions, PrintJob


class BasePrinterAdapter(ABC):
    """Abstract Base Class for OS-specific printer operations."""

    @abstractmethod
    def list_installed_printers(self) -> List[PrinterDevice]:
        """Returns all printers currently installed on the local operating system."""
        pass

    @abstractmethod
    def install_printer(self, device: PrinterDevice, driver_name: Optional[str] = None) -> bool:
        """Installs a printer on the operating system."""
        pass

    @abstractmethod
    def remove_printer(self, printer_name: str) -> bool:
        """Uninstalls/removes a printer from the operating system."""
        pass

    @abstractmethod
    def set_default_printer(self, printer_name: str) -> bool:
        """Sets a printer as the default system printer."""
        pass

    @abstractmethod
    def print_file(self, printer_name: str, file_path: str, options: Optional[PrintJobOptions] = None) -> PrintJob:
        """Submits a print job through the operating system's native spooler."""
        pass

    @abstractmethod
    def list_available_drivers(self) -> List[str]:
        """Returns all printer drivers currently available in the OS driver store."""
        pass
