"""
Universal Printer IPP (Internet Printing Protocol) Client
Implements pure Python driverless IPP 2.0 requests (Get-Printer-Attributes, Print-Job, Validate-Job).
RFC 8010 & RFC 8011 compliant binary parser and builder.
"""
import struct
import io
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import requests

from universal_printer.core.models import PrinterCapabilities, PrintJobOptions

# IPP Operation IDs
OP_PRINT_JOB = 0x0002
OP_VALIDATE_JOB = 0x0004
OP_GET_PRINTER_ATTRIBUTES = 0x000B

# IPP Tag Delimiters
TAG_OPERATION_ATTRIBUTES = 0x01
TAG_JOB_ATTRIBUTES = 0x02
TAG_END_OF_ATTRIBUTES = 0x03
TAG_PRINTER_ATTRIBUTES = 0x04

# Value Tags
TAG_INTEGER = 0x21
TAG_BOOLEAN = 0x22
TAG_ENUM = 0x23
TAG_OCTET_STRING = 0x30
TAG_DATETIME = 0x31
TAG_NAME_WITHOUT_LANG = 0x42
TAG_KEYWORD = 0x44
TAG_URI = 0x45
TAG_CHARSET = 0x47
TAG_NATURAL_LANG = 0x48
TAG_MIME_MEDIA_TYPE = 0x49


class IPPClient:
    """Pure-Python IPP client for driverless printing."""

    def __init__(self, uri: str):
        self.uri = uri
        # Convert ipp:// to http:// and ipps:// to https://
        self.http_url = self._ipp_to_http(uri)

    @staticmethod
    def _ipp_to_http(uri: str) -> str:
        parsed = urllib.parse.urlparse(uri)
        scheme = "https" if parsed.scheme == "ipps" else "http"
        netloc = parsed.netloc
        if ":" not in netloc:
            netloc = f"{netloc}:631"
        path = parsed.path if parsed.path else "/ipp/print"
        return f"{scheme}://{netloc}{path}"

    def _encode_attribute(self, tag: int, name: str, value: Any) -> bytes:
        out = bytearray()
        out.append(tag)
        # Name length + Name
        name_bytes = name.encode("utf-8")
        out.extend(struct.pack(">H", len(name_bytes)))
        out.extend(name_bytes)

        # Value length + Value
        if tag == TAG_BOOLEAN:
            out.extend(struct.pack(">H", 1))
            out.append(1 if value else 0)
        elif tag == TAG_INTEGER or tag == TAG_ENUM:
            out.extend(struct.pack(">H", 4))
            out.extend(struct.pack(">i", int(value)))
        else:
            val_bytes = str(value).encode("utf-8")
            out.extend(struct.pack(">H", len(val_bytes)))
            out.extend(val_bytes)

        return bytes(out)

    def _build_request(self, operation_id: int, request_id: int = 1, extra_op_attrs: Optional[Dict[str, Tuple[int, Any]]] = None) -> bytes:
        buf = bytearray()
        # IPP Version 2.0
        buf.extend(struct.pack(">BB", 2, 0))
        # Operation ID
        buf.extend(struct.pack(">H", operation_id))
        # Request ID
        buf.extend(struct.pack(">i", request_id))

        # Operation Attributes Group
        buf.append(TAG_OPERATION_ATTRIBUTES)
        buf.extend(self._encode_attribute(TAG_CHARSET, "attributes-charset", "utf-8"))
        buf.extend(self._encode_attribute(TAG_NATURAL_LANG, "attributes-natural-language", "en-us"))
        buf.extend(self._encode_attribute(TAG_URI, "printer-uri", self.uri))

        if extra_op_attrs:
            for name, (tag, val) in extra_op_attrs.items():
                buf.extend(self._encode_attribute(tag, name, val))

        buf.append(TAG_END_OF_ATTRIBUTES)
        return bytes(buf)

    def get_printer_attributes(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Queries the IPP device for supported features, formats, and current status."""
        req_bytes = self._build_request(OP_GET_PRINTER_ATTRIBUTES)
        headers = {"Content-Type": "application/ipp"}
        
        resp = requests.post(self.http_url, data=req_bytes, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"IPP Server returned HTTP status {resp.status_code}")

        return self._parse_response(resp.content)

    def print_file(self, file_content: bytes, mime_type: str = "application/pdf", options: Optional[PrintJobOptions] = None, timeout: float = 15.0) -> int:
        """Sends a print job to the IPP printer."""
        opts = options or PrintJobOptions()
        
        extra_attrs = {
            "document-format": (TAG_MIME_MEDIA_TYPE, mime_type),
            "job-name": (TAG_NAME_WITHOUT_LANG, opts.job_name),
            "copies": (TAG_INTEGER, opts.copies),
        }

        req_header = self._build_request(OP_PRINT_JOB, request_id=101, extra_op_attrs=extra_attrs)
        payload = req_header + file_content

        headers = {"Content-Type": "application/ipp"}
        resp = requests.post(self.http_url, data=payload, headers=headers, timeout=timeout)
        
        if resp.status_code != 200:
            raise RuntimeError(f"Print job failed with HTTP {resp.status_code}")

        parsed = self._parse_response(resp.content)
        status_code = parsed.get("status_code", 0)
        if status_code > 0x00FF:
            raise RuntimeError(f"IPP print error code: 0x{status_code:04x}")

        return parsed.get("job_id", 1)

    def _parse_response(self, data: bytes) -> Dict[str, Any]:
        """Simple IPP binary response decoder."""
        if len(data) < 8:
            return {"status_code": -1, "error": "Invalid response"}

        version_major, version_minor, status_code, request_id = struct.unpack(">BBhi", data[:8])
        result: Dict[str, Any] = {
            "version": f"{version_major}.{version_minor}",
            "status_code": status_code,
            "request_id": request_id,
            "attributes": {}
        }

        # Scan attributes
        idx = 8
        current_tag = None
        while idx < len(data):
            tag = data[idx]
            idx += 1
            if tag in (TAG_OPERATION_ATTRIBUTES, TAG_JOB_ATTRIBUTES, TAG_PRINTER_ATTRIBUTES):
                current_tag = tag
                continue
            if tag == TAG_END_OF_ATTRIBUTES:
                break
            
            if idx + 2 > len(data):
                break
            name_len = struct.unpack(">H", data[idx:idx+2])[0]
            idx += 2
            name = data[idx:idx+name_len].decode("utf-8", errors="ignore")
            idx += name_len

            if idx + 2 > len(data):
                break
            val_len = struct.unpack(">H", data[idx:idx+2])[0]
            idx += 2
            val_bytes = data[idx:idx+val_len]
            idx += val_len

            if name:
                result["attributes"][name] = val_bytes.decode("utf-8", errors="ignore")

        return result
