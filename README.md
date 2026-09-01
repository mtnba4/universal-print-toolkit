# Universal Print Toolkit (UPT) 🖨️

> The cross-platform, driverless printing engine and management toolkit for **Windows**, **Linux**, and **macOS**.

---

> [!WARNING]
> ### 🧪 Experimental / Vibecoded Project — Testers & Feedback Needed!
> **Full Transparency:** This project was largely **vibecoded with AI** as an ambitious experiment to unify cross-platform printer discovery, driverless IPP, OS spooler bridges, and document rasterization into a single clean toolkit.
> 
> Because printer hardware, vendor firmwares, network spoolers, and OS printing architectures (Windows Print Spooler vs. CUPS) are notoriously diverse and quirky in the real world:
> - **We need testers!** If you have physical printers (HP, Epson, Brother, Canon, thermal receipt POS, network lasers, or USB setups), please test this tool on Windows, Linux, and macOS.
> - **Report quirks & bugs:** Open an issue or submit a PR with your printer model, OS version, and any logs or strange behavior you encounter.
> - **Feedback & contributions are warmly welcome!** 🤝

---

## 🌟 Features

- **🔍 Auto-Discovery**: Scan your network in seconds for IPP, AirPrint, Mopria, and JetDirect (9100) printers via mDNS/Bonjour.
- **⚡ Driverless Network Printing**: Built-in pure-Python IPP 2.0 (RFC 8010/8011) and Raw Socket client. Print directly without installing vendor bloatware.
- **🌉 Cross-Platform OS Bridge**:
  - **Windows**: Manages Windows Print Spooler (`winspool.drv`, PowerShell `PrintManagement`, `PrintUI`).
  - **Linux & macOS**: Direct integration with CUPS (`lpadmin`, `lpstat`, `lpoptions`, `lp`).
- **📄 Universal Document Pipeline**: Automatically translates text files, markdown, logs, and images (PNG, JPG, TIFF, WebP) into 300 DPI PDF, PWG-Raster, PostScript, PCL6, or ESC/POS thermal receipt streams.
- **🖥️ Web UI & CLI**: Manage printers via a sleek dark-mode Web Dashboard or powerful terminal commands (`upt`).

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/mtnba4/universal-print-toolkit.git
cd universal-print-toolkit
python -m pip install -e .
```

> **Tip:** You can run commands using `upt <command>` or `python -m universal_printer.cli <command>`.

---

## 💻 CLI Usage (`upt`)

### 1. Scan for Printers
```bash
upt scan
```

### 2. List Installed Printers & System Drivers
```bash
upt list
upt drivers
```

### 3. Install a Printer (Driverless or Custom)
```bash
# Auto-detect driverless IPP printer
upt install "Office_Laser" "192.168.1.100"

# Specific driver emulation
upt install "Thermal_Receipt" "192.168.1.200" --driver "Generic / Text Only"
```

### 4. Print Any Document
```bash
# Print via OS Print Spooler
upt print "Microsoft Print to PDF" document.txt

# Direct network print (bypassing OS drivers completely)
upt print "ipp://192.168.1.50/ipp/print" invoice.pdf --direct
```

### 5. Launch the Web Dashboard
```bash
upt web --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## 🤝 Contributing & Testing

1. Clone the repo.
2. Test against your local physical and network printers.
3. Share your findings or create a PR to expand support for specific quirks or obscure PDL protocols!
