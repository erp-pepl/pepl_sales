from __future__ import annotations

import ipaddress
import json
import re
import socket
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import now_datetime
from pypdf import PdfReader


MAX_SOURCE_PDF_BYTES = 25 * 1024 * 1024
MAX_LINK_COUNT = 40
MAX_LINK_DOWNLOAD_BYTES = 15 * 1024 * 1024
MAX_REDIRECTS = 3

ALLOWED_DOWNLOAD_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

ALLOWED_GEM_HOSTS = {
    "gem.gov.in",
    "mkp.gem.gov.in",
    "bidplus.gem.gov.in",
}


def _clean_text(value):
    return re.sub(r"[ \t]+", " ", (value or "")).strip()


def _normalise_multiline_text(value):
    lines = []

    for line in (value or "").splitlines():
        cleaned = _clean_text(line)

        if cleaned:
            lines.append(cleaned)

    return "\n".join(lines)


def _get_attached_file_content(file_url):
    file_name = frappe.db.get_value(
        "File",
        {"file_url": file_url},
        "name",
    )

    if not file_name:
        frappe.throw(
            _("Attached file {0} was not found.").format(file_url)
        )

    file_doc = frappe.get_doc("File", file_name)

    return file_doc.get_content()


def _extract_pdf_text(reader):
    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        pages.append(
            {
                "page": page_number,
                "text": _normalise_multiline_text(text),
            }
        )

    return pages


def _extract_pdf_links(reader):
    links = []
    seen = set()

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        annotations = page.get("/Annots") or []

        for annotation_reference in annotations:
            try:
                annotation = annotation_reference.get_object()
            except Exception:
                continue

            action = annotation.get("/A")

            if not action:
                continue

            uri = action.get("/URI")

            if not uri:
                continue

            uri = str(uri).strip()

            if not uri or uri in seen:
                continue

            seen.add(uri)

            parsed = urlparse(uri)
            hostname = (parsed.hostname or "").lower()

            links.append(
                {
                    "page": page_number,
                    "url": uri,
                    "host": hostname,
                    "link_type": (
                        "GeM Document"
                        if _is_allowed_gem_hostname(hostname)
                        else "External Link"
                    ),
                }
            )

            if len(links) >= MAX_LINK_COUNT:
                return links

    return links


def _first_match(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)

        if match:
            value = _clean_text(match.group(1))

            if value:
                return value

    return None


def _parse_gem_tender(text):
    """Extract stable GeM Tender header information.

    GeM PDFs contain bilingual labels and formatting varies between
    releases. Separators such as ':' are therefore treated as optional.
    """

    result = {}

    separator = r"\s*(?::|-)?\s*"

    result["bid_number"] = _first_match(
        [
            r"Bid\s*Number"
            + separator
            + r"([A-Z0-9][A-Z0-9/\-]+)",
            r"Bid\s*No\.?"
            + separator
            + r"([A-Z0-9][A-Z0-9/\-]+)",
        ],
        text,
    )

    result["publication_date"] = _first_match(
        [
            r"(?:Dated|Published\s+On)"
            + separator
            + r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        ],
        text,
    )

    result["bid_end"] = _first_match(
        [
            r"Bid\s*End\s*Date\s*/?\s*Time"
            + separator
            + r"("
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
            r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
            r")",
        ],
        text,
    )

    result["bid_opening"] = _first_match(
        [
            r"Bid\s*Opening\s*Date\s*/?\s*Time"
            + separator
            + r"("
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
            r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
            r")",
        ],
        text,
    )

    result["ministry"] = _first_match(
        [
            r"Ministry\s*/?\s*State\s*Name"
            + separator
            + r"([^\n]+)",
            r"Ministry"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["department"] = _first_match(
        [
            r"Department\s*Name"
            + separator
            + r"([^\n]+)",
            r"Department"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["organisation"] = _first_match(
        [
            r"Organi[sz]ation\s*Name"
            + separator
            + r"([^\n]+)",
            r"Organi[sz]ation"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["office"] = _first_match(
        [
            r"Office\s*Name"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["total_quantity"] = _first_match(
        [
            r"Total\s*Quantity"
            + separator
            + r"([\d,.]+)",
        ],
        text,
    )

    result["item_category"] = _first_match(
        [
            r"Item\s*Category"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["bid_validity"] = _first_match(
        [
            r"Bid\s*Offer\s*Validity"
            r"(?:\s*\(From\s*End\s*Date\))?"
            + separator
            + r"([^\n]+)",
        ],
        text,
    )

    result["emd_required"] = _first_match(
        [
            r"EMD\s*Detail.*?"
            r"Required"
            + separator
            + r"(Yes|No)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    result["epbg_percentage"] = _first_match(
        [
            r"ePBG\s*Percentage\s*\(%\)"
            + separator
            + r"([\d.]+)",
        ],
        text,
    )

    result["epbg_duration_months"] = _first_match(
        [
            r"Duration\s*of\s*ePBG"
            r"\s*required\s*\(Months\)\.?"
            + separator
            + r"([\d.]+)",
        ],
        text,
    )

    result["splitting_applied"] = _first_match(
        [
            r"Splitting\s*Applied"
            + separator
            + r"(Yes|No)",
        ],
        text,
    )

    result["splitting_ratio"] = _first_match(
        [
            r"Split\s*Criteria.*?"
            r"(\d+\s*:\s*\d+)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return result

def _parse_date(value):
    if not value:
        return None

    for pattern in (
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(
                value,
                pattern,
            ).date().isoformat()
        except ValueError:
            continue

    return None


def _parse_datetime(value):
    if not value:
        return None

    for pattern in (
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ):
        try:
            return datetime.strptime(
                value,
                pattern,
            ).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return None


def _build_summary(parsed, links, page_count):
    lines = [
        f"PDF Pages: {page_count}",
        f"Tender / Bid Reference: {parsed.get('bid_number') or 'Not detected'}",
        f"Publication Date: {parsed.get('publication_date') or 'Not detected'}",
        f"Bid Closing: {parsed.get('bid_end') or 'Not detected'}",
        f"Bid Opening: {parsed.get('bid_opening') or 'Not detected'}",
        f"Bid Validity: {parsed.get('bid_validity') or 'Not detected'}",
        f"Ministry: {parsed.get('ministry') or 'Not detected'}",
        f"Department: {parsed.get('department') or 'Not detected'}",
        f"Organisation: {parsed.get('organisation') or 'Not detected'}",
        f"Office: {parsed.get('office') or 'Not detected'}",
        f"Item Category: {parsed.get('item_category') or 'Not detected'}",
        f"Total Quantity: {parsed.get('total_quantity') or 'Not detected'}",
        f"EMD Required: {parsed.get('emd_required') or 'Not detected'}",
        f"ePBG Percentage: {parsed.get('epbg_percentage') or 'Not detected'}",
        f"ePBG Duration (Months): {parsed.get('epbg_duration_months') or 'Not detected'}",
        f"Splitting Applied: {parsed.get('splitting_applied') or 'Not detected'}",
        f"Splitting Ratio: {parsed.get('splitting_ratio') or 'Not detected'}",
        f"Hyperlinks Discovered: {len(links)}",
    ]

    return "\n".join(lines)

def _build_warnings(parsed, pages):
    warnings = []

    extracted_text = "\n".join(
        page["text"]
        for page in pages
    ).strip()

    if not extracted_text:
        warnings.append(
            "No machine-readable text was found in the uploaded PDF. "
            "This document may be scanned and may require OCR/manual review."
        )

    if not parsed.get("bid_number"):
        warnings.append(
            "Tender / Bid reference could not be detected automatically."
        )

    if not parsed.get("bid_end"):
        warnings.append(
            "Bid submission deadline could not be detected automatically."
        )

    return warnings


def _is_allowed_gem_hostname(hostname):
    hostname = (hostname or "").lower().rstrip(".")

    if hostname in ALLOWED_GEM_HOSTS:
        return True

    return hostname.endswith(".gem.gov.in")


def _assert_public_ip(hostname):
    try:
        answers = socket.getaddrinfo(
            hostname,
            443,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        frappe.throw(
            _("Unable to resolve Tender link host {0}: {1}").format(
                hostname,
                exc,
            )
        )

    addresses = {
        answer[4][0]
        for answer in answers
    }

    for address in addresses:
        ip = ipaddress.ip_address(address)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            frappe.throw(
                _(
                    "Tender link resolved to a non-public address "
                    "and was blocked."
                )
            )


def _validate_download_url(url):
    parsed = urlparse(url)

    if parsed.scheme.lower() != "https":
        frappe.throw(
            _("Only HTTPS Tender hyperlinks can be downloaded automatically.")
        )

    hostname = (parsed.hostname or "").lower()

    if not _is_allowed_gem_hostname(hostname):
        frappe.throw(
            _(
                "Automatic Tender download is restricted to approved "
                "GeM domains. Host blocked: {0}"
            ).format(hostname or _("Unknown"))
        )

    _assert_public_ip(hostname)

    return hostname


def _download_allowed_url(url):
    import requests

    current_url = url

    for redirect_index in range(MAX_REDIRECTS + 1):
        _validate_download_url(current_url)

        response = requests.get(
            current_url,
            stream=True,
            timeout=(5, 20),
            allow_redirects=False,
            headers={
                "User-Agent": (
                    "PEPL-Sales-Tender-Ingestion/1.0"
                ),
            },
        )

        if response.status_code in {
            301,
            302,
            303,
            307,
            308,
        }:
            if redirect_index >= MAX_REDIRECTS:
                raise RuntimeError(
                    "Maximum Tender-link redirects exceeded."
                )

            location = response.headers.get("Location")

            if not location:
                raise RuntimeError(
                    "Tender-link redirect had no Location header."
                )

            from urllib.parse import urljoin

            current_url = urljoin(
                current_url,
                location,
            )
            continue

        response.raise_for_status()

        content_length = response.headers.get(
            "Content-Length"
        )

        if (
            content_length
            and int(content_length) > MAX_LINK_DOWNLOAD_BYTES
        ):
            raise RuntimeError(
                "Linked Tender file exceeds the automatic "
                "download size limit."
            )

        content = bytearray()

        for chunk in response.iter_content(
            chunk_size=64 * 1024
        ):
            if not chunk:
                continue

            content.extend(chunk)

            if len(content) > MAX_LINK_DOWNLOAD_BYTES:
                raise RuntimeError(
                    "Linked Tender file exceeds the automatic "
                    "download size limit."
                )

        filename = Path(
            urlparse(current_url).path
        ).name or "tender_linked_document"

        extension = Path(filename).suffix.lower()

        if (
            extension
            and extension not in ALLOWED_DOWNLOAD_EXTENSIONS
        ):
            raise RuntimeError(
                f"Linked file type {extension} is not approved."
            )

        return {
            "content": bytes(content),
            "filename": filename,
            "final_url": current_url,
            "content_type": response.headers.get(
                "Content-Type",
                "",
            ),
        }

    raise RuntimeError(
        "Unable to retrieve linked Tender document."
    )


def _attach_content(
    *,
    content,
    filename,
    tender_name,
    attached_to_field=None,
):
    values = {
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": "PEPL Tender",
        "attached_to_name": tender_name,
        "content": content,
        "is_private": 1,
    }

    if attached_to_field:
        values["attached_to_field"] = attached_to_field

    file_doc = frappe.get_doc(values)
    file_doc.insert(ignore_permissions=True)

    return file_doc.file_url


def _populate_source_links(tender, links):
    tender.set(
        "tender_source_links",
        [],
    )

    for link in links:
        status = (
            "Discovered"
            if link["link_type"] == "GeM Document"
            else "Manual Review Required"
        )

        tender.append(
            "tender_source_links",
            {
                "source_url": link["url"],
                "source_host": link["host"],
                "link_type": link["link_type"],
                "retrieval_status": status,
                "remarks": (
                    f"Discovered on PDF page {link['page']}."
                ),
            },
        )


def _set_safe_extracted_fields(tender, parsed):
    """
    Only populate blank, non-Link values.

    Customer, Sector, Items and commercial fields are intentionally
    never inferred or overwritten here.
    """

    if (
        not tender.nit_number
        and parsed.get("bid_number")
    ):
        tender.nit_number = parsed["bid_number"]

    if (
        not tender.publication_date
        and parsed.get("publication_date")
    ):
        tender.publication_date = _parse_date(
            parsed["publication_date"]
        )

    if (
        not tender.bid_submission_deadline
        and parsed.get("bid_end")
    ):
        tender.bid_submission_deadline = _parse_datetime(
            parsed["bid_end"]
        )

    if (
        not tender.bid_opening_date
        and parsed.get("bid_opening")
    ):
        tender.bid_opening_date = _parse_datetime(
            parsed["bid_opening"]
        )


@frappe.whitelist()
def read_tender_pdf(tender_name):
    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    tender.check_permission("write")

    if tender.docstatus != 0:
        frappe.throw(
            _("Tender PDF can be read only while the Tender is in Draft.")
        )

    if not tender.tender_source_pdf:
        frappe.throw(
            _("Upload Original Tender PDF first.")
        )

    if not tender.tender_source_pdf.lower().endswith(
        ".pdf"
    ):
        frappe.throw(
            _("Original Tender file must be a PDF.")
        )

    try:
        content = _get_attached_file_content(
            tender.tender_source_pdf
        )

        if len(content) > MAX_SOURCE_PDF_BYTES:
            frappe.throw(
                _("Tender PDF exceeds the 25 MB reading limit.")
            )

        reader = PdfReader(
            BytesIO(content)
        )

        pages = _extract_pdf_text(reader)
        links = _extract_pdf_links(reader)

        full_text = "\n\n".join(
            page["text"]
            for page in pages
        )

        parsed = _parse_gem_tender(
            full_text
        )

        warnings = _build_warnings(
            parsed,
            pages,
        )

        extraction = {
            "engine_version": "1.0",
            "source_file": tender.tender_source_pdf,
            "page_count": len(reader.pages),
            "parsed": parsed,
            "links": links,
            "pages": pages,
            "warnings": warnings,
        }

        _populate_source_links(
            tender,
            links,
        )

        _set_safe_extracted_fields(
            tender,
            parsed,
        )

        tender.tender_ingestion_summary = (
            _build_summary(
                parsed,
                links,
                len(reader.pages),
            )
        )

        tender.tender_extraction_json = (
            json.dumps(
                extraction,
                ensure_ascii=False,
                indent=2,
            )
        )

        tender.tender_ingestion_warnings = (
            "\n".join(warnings)
        )

        tender.tender_ingestion_status = (
            "Read with Warnings"
            if warnings
            else "Read - Review Required"
        )

        tender.tender_ingestion_last_run = (
            now_datetime()
        )

        tender.save()

        return {
            "status": tender.tender_ingestion_status,
            "page_count": len(reader.pages),
            "link_count": len(links),
            "parsed": parsed,
            "warning_count": len(warnings),
            "warnings": warnings,
        }

    except Exception as exc:
        frappe.log_error(
            frappe.get_traceback(),
            "PEPL Tender Automatic Reading",
        )

        tender.db_set(
            "tender_ingestion_status",
            "Failed",
            update_modified=False,
        )

        tender.db_set(
            "tender_ingestion_warnings",
            str(exc),
            update_modified=True,
        )

        raise


@frappe.whitelist()
def download_discovered_gem_documents(
    tender_name,
):
    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    tender.check_permission("write")

    if tender.docstatus != 0:
        frappe.throw(
            _("Linked Tender files can be retrieved only in Draft.")
        )

    downloaded = 0
    failed = 0
    skipped = 0

    for row in tender.tender_source_links or []:
        if row.link_type != "GeM Document":
            skipped += 1
            continue

        if row.downloaded_file:
            skipped += 1
            continue

        try:
            result = _download_allowed_url(
                row.source_url
            )

            file_url = _attach_content(
                content=result["content"],
                filename=result["filename"],
                tender_name=tender.name,
            )

            row.downloaded_file = file_url
            row.retrieval_status = "Downloaded"
            row.remarks = (
                "Downloaded securely from approved GeM host."
            )
            downloaded += 1

        except Exception as exc:
            row.retrieval_status = "Failed"
            row.remarks = str(exc)[:500]
            failed += 1

    tender.save()

    return {
        "downloaded": downloaded,
        "failed": failed,
        "skipped": skipped,
    }


@frappe.whitelist()
def mark_tender_extraction_reviewed(
    tender_name,
):
    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    tender.check_permission("write")

    if tender.docstatus != 0:
        frappe.throw(
            _("Extraction review can be completed only in Draft.")
        )

    if tender.tender_ingestion_status not in {
        "Read - Review Required",
        "Read with Warnings",
        "Reviewed",
    }:
        frappe.throw(
            _("Read the Tender PDF before completing extraction review.")
        )

    tender.tender_ingestion_status = "Reviewed"
    tender.save()

    tender.add_comment(
        "Comment",
        text=(
            "Tender automatic extraction reviewed by "
            f"{frappe.session.user}."
        ),
    )

    return {
        "status": "Reviewed",
    }


def _set_docx_defaults(document):
    from docx.shared import Inches, Pt

    styles = document.styles

    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)

    for section in document.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)


def _add_key_value_table(
    document,
    rows,
):
    table = document.add_table(
        rows=0,
        cols=2,
    )

    try:
        table.style = "Table Grid"
    except KeyError:
        pass

    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = (
            str(value)
            if value not in (None, "")
            else "-"
        )

        if cells[0].paragraphs:
            run = cells[0].paragraphs[0].runs[0]
            run.bold = True

    return table


def _load_word_letterhead():
    from docx import Document as WordDocument

    letterhead_path = Path(
        frappe.get_app_path(
            "pepl_sales",
            "public",
            "letterhead",
            "PEPL_Letterhead_Plain.docx",
        )
    )

    if letterhead_path.exists():
        return WordDocument(
            str(letterhead_path)
        )

    return WordDocument()


@frappe.whitelist()
def generate_tender_word(
    tender_name,
):
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    tender.check_permission("read")

    if tender.tender_ingestion_status not in {
        "Reviewed",
        "Read - Review Required",
        "Read with Warnings",
    }:
        frappe.throw(
            _("Read the Tender PDF before generating the Word document.")
        )

    extraction = {}

    if tender.tender_extraction_json:
        try:
            extraction = json.loads(
                tender.tender_extraction_json
            )
        except json.JSONDecodeError:
            extraction = {}

    parsed = extraction.get(
        "parsed",
        {},
    )

    document = _load_word_letterhead()
    _set_docx_defaults(document)

    title = document.add_heading(
        "TENDER REVIEW / BID PREPARATION DOCUMENT",
        level=1,
    )
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    paragraph = document.add_paragraph()
    paragraph.add_run(
        "Generated automatically from uploaded Tender documents. "
    ).bold = True
    paragraph.add_run(
        "All extracted information must be reviewed against the "
        "original tender before bid submission."
    )

    document.add_heading(
        "1. Tender Identification",
        level=2,
    )

    _add_key_value_table(
        document,
        [
            (
                "PEPL Tender",
                tender.name,
            ),
            (
                "Tender / NIT Reference",
                tender.nit_number
                or parsed.get("bid_number"),
            ),
            (
                "Tender Title",
                tender.tender_title,
            ),
            (
                "Customer",
                tender.customer,
            ),
            (
                "Sector",
                tender.sector,
            ),
            (
                "Portal URL",
                tender.tender_portal_url,
            ),
        ],
    )

    document.add_heading(
        "2. Critical Dates",
        level=2,
    )

    _add_key_value_table(
        document,
        [
            (
                "Publication Date",
                tender.publication_date
                or parsed.get("publication_date"),
            ),
            (
                "Bid Submission Deadline",
                tender.bid_submission_deadline
                or parsed.get("bid_end"),
            ),
            (
                "Bid Opening",
                tender.bid_opening_date
                or parsed.get("bid_opening"),
            ),
            (
                "Pre-Bid Meeting",
                tender.pre_bid_meeting_date,
            ),
        ],
    )

    document.add_heading(
        "3. Extracted Organisation Information",
        level=2,
    )

    _add_key_value_table(
        document,
        [
            (
                "Ministry",
                parsed.get("ministry"),
            ),
            (
                "Department",
                parsed.get("department"),
            ),
            (
                "Organisation",
                parsed.get("organisation"),
            ),
            (
                "Total Quantity Found in Tender",
                parsed.get("total_quantity"),
            ),
        ],
    )

    document.add_heading(
        "4. Tender Items in ERPNext",
        level=2,
    )

    if tender.items:
        table = document.add_table(
            rows=1,
            cols=7,
        )

        try:
            table.style = "Table Grid"
        except KeyError:
            pass

        headings = [
            "Item",
            "PL No",
            "Drawing",
            "Specification",
            "Quantity",
            "UOM",
            "Vendor Approval",
        ]

        for index, heading in enumerate(
            headings
        ):
            table.rows[0].cells[index].text = heading

        for item in tender.items:
            cells = table.add_row().cells

            values = [
                item.item,
                item.pl_no,
                item.drawing_no,
                item.current_specification,
                item.quantity,
                item.uom,
                (
                    f"{item.vendor_approval_stage or '-'} / "
                    f"{item.vendor_approval_health or '-'}"
                ),
            ]

            for index, value in enumerate(
                values
            ):
                cells[index].text = (
                    str(value)
                    if value not in (
                        None,
                        "",
                    )
                    else "-"
                )
    else:
        document.add_paragraph(
            "Tender Items have not yet been mapped to ERPNext Item Master."
        )

    document.add_heading(
        "5. EMD / Bid Security",
        level=2,
    )

    _add_key_value_table(
        document,
        [
            (
                "Bid Securing Declaration",
                "Yes"
                if tender.bid_securing_declaration
                else "No",
            ),
            (
                "EMD Required",
                "Yes"
                if tender.emd_required
                else "No",
            ),
            (
                "EMD Amount",
                tender.emd_amount,
            ),
            (
                "EMD Mode",
                tender.emd_mode,
            ),
        ],
    )

    document.add_heading(
        "6. Required Bid Documents",
        level=2,
    )

    if tender.bid_documents:
        table = document.add_table(
            rows=1,
            cols=4,
        )

        try:
            table.style = "Table Grid"
        except KeyError:
            pass

        for index, heading in enumerate(
            [
                "Document",
                "Source",
                "Mandatory",
                "Attached",
            ]
        ):
            table.rows[0].cells[index].text = heading

        for row in tender.bid_documents:
            cells = table.add_row().cells
            cells[0].text = (
                row.document_type
                or row.document_name
                or "-"
            )
            cells[1].text = row.document_source or "-"
            cells[2].text = (
                "Yes"
                if row.is_mandatory
                else "No"
            )
            cells[3].text = (
                "Yes"
                if row.is_attached
                else "No"
            )
    else:
        document.add_paragraph(
            "Bid-document checklist has not yet been generated."
        )

    document.add_heading(
        "7. Hyperlinks / Tender Attachments Discovered",
        level=2,
    )

    if tender.tender_source_links:
        table = document.add_table(
            rows=1,
            cols=4,
        )

        try:
            table.style = "Table Grid"
        except KeyError:
            pass

        for index, heading in enumerate(
            [
                "Type",
                "URL",
                "Retrieval Status",
                "Local File",
            ]
        ):
            table.rows[0].cells[index].text = heading

        for row in tender.tender_source_links:
            cells = table.add_row().cells
            cells[0].text = row.link_type or "-"
            cells[1].text = row.source_url or "-"
            cells[2].text = row.retrieval_status or "-"
            cells[3].text = row.downloaded_file or "-"
    else:
        document.add_paragraph(
            "No hyperlinks were discovered in the source PDF."
        )

    document.add_heading(
        "8. Automatic Reading Warnings",
        level=2,
    )

    if tender.tender_ingestion_warnings:
        document.add_paragraph(
            tender.tender_ingestion_warnings
        )
    else:
        document.add_paragraph(
            "No automatic-reading warnings were recorded."
        )

    document.add_heading(
        "9. Manual Review",
        level=2,
    )

    document.add_paragraph(
        "Tender reference verified: ______________________________"
    )
    document.add_paragraph(
        "Technical requirements verified: _________________________"
    )
    document.add_paragraph(
        "Commercial requirements verified: ________________________"
    )
    document.add_paragraph(
        "Bid documents verified: _________________________________"
    )
    document.add_paragraph(
        "Reviewed by: ______________________  Date: ______________"
    )

    output = BytesIO()
    document.save(output)

    output.seek(0)

    safe_reference = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        tender.nit_number or tender.name,
    )

    filename = (
        f"PEPL_Tender_Review_{safe_reference}.docx"
    )

    file_url = _attach_content(
        content=output.getvalue(),
        filename=filename,
        tender_name=tender.name,
        attached_to_field="generated_tender_word",
    )

    tender.db_set(
        "generated_tender_word",
        file_url,
        update_modified=True,
    )

    tender.add_comment(
        "Comment",
        text=(
            "Editable Tender Word document generated by "
            f"{frappe.session.user}: {file_url}"
        ),
    )

    return {
        "file_url": file_url,
        "filename": filename,
    }
