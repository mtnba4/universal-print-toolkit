"""
Universal Printer CLI Interface
Interactive cross-platform command-line tool built with Typer & Rich.
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from universal_printer.manager import UniversalPrinterManager
from universal_printer.core.models import PrintJobOptions, PageOrientation, ColorMode
from universal_printer.drivers.registry import DriverRegistry

app = typer.Typer(
    name="universal-print-toolkit",
    help="Universal Print Toolkit (UPT) - Cross-platform tool to discover, install, configure, and use any printer or driver across Windows, Linux, and macOS."
)
console = Console()
manager = UniversalPrinterManager()


@app.command("scan")
def scan(
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Scan duration in seconds")
):
    """Scan the local network for IPP, AirPrint, and Mopria printers."""
    console.print(f"[bold cyan]Scanning local network for printers ({timeout}s)...[/bold cyan]")
    printers = manager.scan_printers(timeout=timeout)

    if not printers:
        console.print("[yellow]No network printers discovered automatically. You can still install manually using IP address.[/yellow]")
        return

    table = Table(title="Discovered Network Printers", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Model / Type", style="green")
    table.add_column("IP / Address", style="yellow")
    table.add_column("URI", style="blue")
    table.add_column("Color", style="white")

    for p in printers:
        color_str = "[green]Yes[/green]" if p.capabilities.supports_color else "[white]Mono[/white]"
        table.add_row(p.name, p.make_and_model, p.address or "N/A", p.uri, color_str)

    console.print(table)


@app.command("list")
def list_printers():
    """List all printers installed on this operating system."""
    console.print("[bold cyan]Retrieving installed OS printers...[/bold cyan]")
    printers = manager.list_installed_printers()

    if not printers:
        console.print("[yellow]No printers currently installed on this OS.[/yellow]")
        return

    table = Table(title="Installed System Printers", show_header=True, header_style="bold blue")
    table.add_column("Printer Name", style="cyan", no_wrap=True)
    table.add_column("Driver / Model", style="green")
    table.add_column("Port / URI", style="yellow")

    for p in printers:
        table.add_row(p.name, p.make_and_model, p.uri or "Local")

    console.print(table)


@app.command("drivers")
def list_drivers():
    """List available universal fallback driver profiles and system drivers."""
    # 1. Universal Profiles
    profiles = DriverRegistry.list_universal_profiles()
    table1 = Table(title="Universal Driver Profiles (Cross-Platform)", show_header=True, header_style="bold green")
    table1.add_column("Profile Name", style="cyan")
    table1.add_column("Category", style="yellow")
    table1.add_column("Emulation", style="magenta")
    table1.add_column("Description", style="white")

    for p in profiles:
        table1.add_row(p.name, p.category, p.emulation, p.description)

    console.print(table1)

    # 2. Local OS Drivers
    sys_drivers = manager.list_available_drivers()
    if sys_drivers:
        table2 = Table(title=f"Installed OS Drivers ({len(sys_drivers)} detected)", show_header=True, header_style="bold cyan")
        table2.add_column("Driver Name", style="white")
        for d in sys_drivers[:15]: # Show top 15
            table2.add_row(d)
        if len(sys_drivers) > 15:
            table2.add_row(f"[dim]... and {len(sys_drivers) - 15} more drivers[/dim]")
        console.print(table2)


@app.command("install")
def install(
    name: str = typer.Argument(..., help="Friendly name for the printer"),
    target: str = typer.Argument(..., help="IP Address or IPP URI (e.g. 192.168.1.100 or ipp://...)"),
    driver: Optional[str] = typer.Option(None, "--driver", "-d", help="Specific driver name or leave empty for auto-driverless")
):
    """Install any printer onto the operating system."""
    console.print(f"[bold cyan]Installing printer '{name}' targeting '{target}'...[/bold cyan]")
    success = manager.install_printer(name=name, uri_or_ip=target, driver_name=driver)
    if success:
        console.print(f"[bold green]Successfully installed printer '{name}'![/bold green]")
    else:
        console.print(f"[bold red]Failed to install printer '{name}'. Please check administrative permissions.[/bold red]")


@app.command("remove")
def remove(
    name: str = typer.Argument(..., help="Name of the printer to uninstall")
):
    """Uninstall a printer from the operating system."""
    success = manager.remove_printer(name)
    if success:
        console.print(f"[bold green]Printer '{name}' removed successfully.[/bold green]")
    else:
        console.print(f"[bold red]Failed to remove printer '{name}'.[/bold red]")


@app.command("default")
def set_default(
    name: str = typer.Argument(..., help="Name of the printer to set as default")
):
    """Set the system default printer."""
    success = manager.set_default_printer(name)
    if success:
        console.print(f"[bold green]Printer '{name}' is now the default system printer.[/bold green]")
    else:
        console.print(f"[bold red]Failed to set default printer.[/bold red]")


@app.command("print")
def print_doc(
    printer: str = typer.Argument(..., help="Printer name or IPP URI / IP address"),
    file: str = typer.Argument(..., help="Path to file to print (PDF, TXT, PNG, etc.)"),
    copies: int = typer.Option(1, "--copies", "-c", help="Number of copies"),
    color: bool = typer.Option(False, "--color", help="Enable color mode"),
    landscape: bool = typer.Option(False, "--landscape", "-l", help="Print in landscape orientation"),
    direct: bool = typer.Option(False, "--direct", help="Send directly via network IPP/Raw bypassing OS spooler")
):
    """Print a document to any printer."""
    opts = PrintJobOptions(
        copies=copies,
        color_mode=ColorMode.COLOR if color else ColorMode.MONOCHROME,
        orientation=PageOrientation.LANDSCAPE if landscape else PageOrientation.PORTRAIT,
        job_name=f"Job-{file}"
    )

    console.print(f"[bold cyan]Submitting print job for '{file}' to '{printer}'...[/bold cyan]")
    try:
        job = manager.print_file(printer_target=printer, file_path=file, options=opts, direct_network=direct)
        console.print(Panel(
            f"[bold green]Print Job Dispatched![/bold green]\n"
            f"Job ID: [cyan]{job.job_id}[/cyan]\n"
            f"Status: [yellow]{job.status}[/yellow]\n"
            f"Target: {job.printer_id}\n"
            f"Bytes: {job.bytes_sent or 'N/A'}",
            title="Print Status"
        ))
    except Exception as e:
        console.print(f"[bold red]Error sending print job:[/bold red] {e}")


@app.command("web")
def run_web(
    port: int = typer.Option(8000, "--port", "-p", help="Web UI dashboard port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Binding host")
):
    """Launch the Universal Printer Web Management Dashboard."""
    import uvicorn
    console.print(f"[bold green]Starting Universal Printer Web Dashboard on http://{host}:{port}[/bold green]")
    uvicorn.run("universal_printer.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
