"""
Universal Printer Web Dashboard API
FastAPI backend providing REST API and interactive Web UI for managing printers.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from typing import List, Optional
import tempfile
import os

from universal_printer.manager import UniversalPrinterManager
from universal_printer.core.models import PrintJobOptions, ColorMode, PageOrientation
from universal_printer.drivers.registry import DriverRegistry

app = FastAPI(title="Universal Print Toolkit (UPT) Dashboard", version="0.1.0")
manager = UniversalPrinterManager()


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Universal Print Toolkit (UPT)</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            body { background: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
            .navbar { background: #1e293b !important; border-bottom: 1px solid #334155; }
            .btn-primary { background: #3b82f6; border: none; }
            .btn-primary:hover { background: #2563eb; }
            .badge-custom { background: #0284c7; }
        </style>
    </head>
    <body class="p-0">
        <nav class="navbar navbar-dark px-4 mb-3">
            <div class="container-fluid">
                <span class="navbar-brand mb-0 h1"><i class="bi bi-printer-fill text-primary me-2"></i>Universal Print Toolkit (UPT)</span>
                <span class="badge bg-warning text-dark"><i class="bi bi-cone-striped me-1"></i>Experimental / Vibecoded — Testers Needed</span>
            </div>
        </nav>
        <div class="container">
            <div class="alert alert-info border-0 shadow-sm mb-4" style="background: #1e3a8a; color: #bfdbfe;">
                <i class="bi bi-info-circle-fill me-2"></i><strong>Community Preview:</strong> This tool is an open-source experiment built with AI. Please test with your hardware and report bugs or hardware quirks on GitHub!
            </div>
            <div class="row g-4">
                <!-- Discovered & Installed -->
                <div class="col-lg-7">
                    <div class="card p-4 shadow-sm mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4 class="m-0"><i class="bi bi-hdd-network me-2 text-info"></i>Discovered Network Printers</h4>
                            <button onclick="scanNetwork()" class="btn btn-sm btn-outline-info" id="scanBtn">
                                <i class="bi bi-arrow-clockwise me-1"></i>Scan Network
                            </button>
                        </div>
                        <div id="scanResults" class="text-muted small">Click 'Scan Network' to search for AirPrint/Mopria/IPP printers...</div>
                    </div>

                    <div class="card p-4 shadow-sm">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4 class="m-0"><i class="bi bi-pc-display me-2 text-success"></i>Installed System Printers</h4>
                            <button onclick="loadInstalled()" class="btn btn-sm btn-outline-success">
                                <i class="bi bi-arrow-clockwise me-1"></i>Refresh
                            </button>
                        </div>
                        <div id="installedResults" class="table-responsive">
                            <div class="spinner-border spinner-border-sm text-primary" role="status"></div> Loading...
                        </div>
                    </div>
                </div>

                <!-- Quick Actions: Install & Print -->
                <div class="col-lg-5">
                    <!-- Quick Print -->
                    <div class="card p-4 shadow-sm mb-4">
                        <h4 class="mb-3"><i class="bi bi-file-earmark-arrow-up me-2 text-warning"></i>Universal Print Job</h4>
                        <form id="printForm" onsubmit="submitPrint(event)">
                            <div class="mb-3">
                                <label class="form-label text-white-50">Target Printer / URI</label>
                                <input type="text" class="form-control bg-dark text-white border-secondary" id="printTarget" required placeholder="e.g. PrinterName or ipp://192.168.1.50">
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-white-50">Document File (PDF, Image, Text)</label>
                                <input type="file" class="form-control bg-dark text-white border-secondary" id="printFile" required>
                            </div>
                            <div class="row g-2 mb-3">
                                <div class="col-6">
                                    <label class="form-label text-white-50">Copies</label>
                                    <input type="number" class="form-control bg-dark text-white border-secondary" id="printCopies" value="1" min="1">
                                </div>
                                <div class="col-6">
                                    <label class="form-label text-white-50">Color</label>
                                    <select class="form-select bg-dark text-white border-secondary" id="printColor">
                                        <option value="false">Grayscale/Mono</option>
                                        <option value="true">Color</option>
                                    </select>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary w-100" id="printBtn">
                                <i class="bi bi-send me-1"></i>Print Document
                            </button>
                            <div id="printAlert" class="mt-3"></div>
                        </form>
                    </div>

                    <!-- Quick Install -->
                    <div class="card p-4 shadow-sm">
                        <h4 class="mb-3"><i class="bi bi-plus-circle me-2 text-primary"></i>Install New Printer</h4>
                        <form id="installForm" onsubmit="submitInstall(event)">
                            <div class="mb-3">
                                <label class="form-label text-white-50">Printer Name</label>
                                <input type="text" class="form-control bg-dark text-white border-secondary" id="installName" required placeholder="e.g. Office_Laser">
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-white-50">Target IP or IPP URI</label>
                                <input type="text" class="form-control bg-dark text-white border-secondary" id="installUri" required placeholder="e.g. 192.168.1.100">
                            </div>
                            <button type="submit" class="btn btn-outline-primary w-100" id="installBtn">
                                <i class="bi bi-download me-1"></i>Install on OS
                            </button>
                            <div id="installAlert" class="mt-3"></div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function loadInstalled() {
                const res = await fetch('/api/printers/installed');
                const data = await res.json();
                let html = '<table class="table table-dark table-hover mb-0"><thead><tr><th>Name</th><th>Driver</th><th>Action</th></tr></thead><tbody>';
                if(data.length === 0) {
                    html += '<tr><td colspan="3" class="text-center text-muted">No printers installed</td></tr>';
                } else {
                    data.forEach(p => {
                        html += `<tr>
                            <td><strong>${p.name}</strong></td>
                            <td class="text-white-50 small">${p.make_and_model}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-info" onclick="selectPrinter('${p.name}')">Select</button>
                            </td>
                        </tr>`;
                    });
                }
                html += '</tbody></table>';
                document.getElementById('installedResults').innerHTML = html;
            }

            async function scanNetwork() {
                const btn = document.getElementById('scanBtn');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Scanning...';
                document.getElementById('scanResults').innerHTML = '<div class="spinner-border spinner-border-sm text-info"></div> Probing network (3s)...';
                
                try {
                    const res = await fetch('/api/printers/scan');
                    const data = await res.json();
                    if(data.length === 0) {
                        document.getElementById('scanResults').innerHTML = '<div class="alert alert-secondary mb-0">No network printers detected.</div>';
                    } else {
                        let html = '<div class="list-group">';
                        data.forEach(p => {
                            html += `<div class="list-group-item list-group-item-dark d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${p.name}</strong><br>
                                    <small class="text-muted">${p.make_and_model} | ${p.uri}</small>
                                </div>
                                <button class="btn btn-sm btn-success" onclick="installScanned('${p.name}', '${p.uri}')">Install</button>
                            </div>`;
                        });
                        html += '</div>';
                        document.getElementById('scanResults').innerHTML = html;
                    }
                } catch(e) {
                    document.getElementById('scanResults').innerHTML = '<div class="alert alert-danger">Scan error: ' + e + '</div>';
                }
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i>Scan Network';
            }

            function selectPrinter(name) {
                document.getElementById('printTarget').value = name;
            }

            function installScanned(name, uri) {
                document.getElementById('installName').value = name;
                document.getElementById('installUri').value = uri;
            }

            async function submitInstall(e) {
                e.preventDefault();
                const name = document.getElementById('installName').value;
                const uri = document.getElementById('installUri').value;
                const btn = document.getElementById('installBtn');
                btn.disabled = true;
                
                const res = await fetch('/api/printers/install', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, target: uri})
                });
                const data = await res.json();
                btn.disabled = false;
                if(data.success) {
                    document.getElementById('installAlert').innerHTML = '<div class="alert alert-success">Printer installed!</div>';
                    loadInstalled();
                } else {
                    document.getElementById('installAlert').innerHTML = '<div class="alert alert-danger">Install failed.</div>';
                }
            }

            async function submitPrint(e) {
                e.preventDefault();
                const fileInput = document.getElementById('printFile');
                if(!fileInput.files[0]) return;

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('printer', document.getElementById('printTarget').value);
                formData.append('copies', document.getElementById('printCopies').value);
                formData.append('color', document.getElementById('printColor').value);

                const btn = document.getElementById('printBtn');
                btn.disabled = true;
                const res = await fetch('/api/printers/print', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                btn.disabled = false;
                if(data.job_id) {
                    document.getElementById('printAlert').innerHTML = `<div class="alert alert-success">Job Sent! ID: ${data.job_id}</div>`;
                } else {
                    document.getElementById('printAlert').innerHTML = `<div class="alert alert-danger">Error: ${data.detail || 'Print failed'}</div>`;
                }
            }

            loadInstalled();
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/api/printers/installed")
async def get_installed():
    return manager.list_installed_printers()


@app.get("/api/printers/scan")
async def scan_network(timeout: float = 3.0):
    return manager.scan_printers(timeout=timeout)


@app.get("/api/drivers")
async def get_drivers():
    return {
        "universal": DriverRegistry.list_universal_profiles(),
        "system": manager.list_available_drivers()
    }


@app.post("/api/printers/install")
async def install_printer_endpoint(payload: dict):
    name = payload.get("name")
    target = payload.get("target")
    driver = payload.get("driver")
    if not name or not target:
        raise HTTPException(status_code=400, detail="name and target are required")
    success = manager.install_printer(name=name, uri_or_ip=target, driver_name=driver)
    return {"success": success, "printer": name}


@app.post("/api/printers/print")
async def print_endpoint(
    printer: str = Form(...),
    copies: int = Form(1),
    color: bool = Form(False),
    file: UploadFile = File(...)
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    opts = PrintJobOptions(
        copies=copies,
        color_mode=ColorMode.COLOR if color else ColorMode.MONOCHROME,
        job_name=file.filename or "Web Print Job"
    )

    try:
        job = manager.print_file(printer_target=printer, file_path=tmp_path, options=opts)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
