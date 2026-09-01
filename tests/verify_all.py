from universal_printer.manager import UniversalPrinterManager
from universal_printer.core.models import PrintJobOptions
from universal_printer.core.pipeline import DocumentPipeline
from universal_printer.drivers.registry import DriverRegistry
import os

print("--- Testing Universal Printer Components ---")

# 1. Test Driver Registry
profiles = DriverRegistry.list_universal_profiles()
print(f"[OK] Driver profiles loaded: {len(profiles)}")
for p in profiles:
    print(f"  - {p.name} ({p.emulation})")

# 2. Test Pipeline (Text to PDF rendering)
test_txt = "test_doc.txt"
with open(test_txt, "w") as f:
    f.write("Universal Printer Support\nLine 1: Cross-platform printing test\nLine 2: Success!")

opts = PrintJobOptions()
pdf_bytes, mime = DocumentPipeline.prepare_document(test_txt, opts, target_format="application/pdf")
print(f"[OK] DocumentPipeline rendered text to PDF: {len(pdf_bytes)} bytes, MIME={mime}")

if os.path.exists(test_txt):
    os.remove(test_txt)

# 3. Test Manager & OS Adapter
mgr = UniversalPrinterManager()
installed = mgr.list_installed_printers()
print(f"[OK] OS Adapter detected {len(installed)} installed printers on {mgr.os_type}:")
for p in installed[:5]:
    print(f"  - {p.name} (Driver: {p.make_and_model})")

drivers = mgr.list_available_drivers()
print(f"[OK] Found {len(drivers)} system drivers registered in OS store.")
