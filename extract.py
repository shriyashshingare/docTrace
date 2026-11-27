"""DocTrace minimal PyMuPDF (fitz) extraction & visual provenance test."""

import argparse
import json
import re
from pathlib import Path
import pymupdf


def create_sample_invoice_pdf(pdf_path: Path) -> Path:
    """Generate a realistic non-image (digital) invoice PDF for testing."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)  # US Letter

    # Header
    page.insert_text((50, 60), "ACME CLOUD INFRASTRUCTURE INC.", fontsize=18, fontname="helv")
    page.insert_text((50, 82), "120 Market Street, Suite 400, San Francisco, CA 94105", fontsize=10, fontname="helv")
    page.insert_text((430, 60), "INVOICE", fontsize=22, fontname="helv")

    # Metadata block
    page.insert_text((430, 95), "Invoice No: INV-2026-0842", fontsize=11, fontname="helv")
    page.insert_text((430, 113), "Issue Date: 2026-11-15", fontsize=11, fontname="helv")
    page.insert_text((430, 131), "Due Date: 2026-12-15", fontsize=11, fontname="helv")

    # Bill To
    page.insert_text((50, 145), "Bill To:", fontsize=11, fontname="helv")
    page.insert_text((50, 162), "DocTrace Labs LLC", fontsize=11, fontname="helv")
    page.insert_text((50, 178), "Attn: Accounts Payable", fontsize=10, fontname="helv")

    # Line items table header
    y = 240
    page.draw_line((50, y - 15), (562, y - 15))
    page.insert_text((50, y), "Description", fontsize=11, fontname="helv")
    page.insert_text((350, y), "Qty", fontsize=11, fontname="helv")
    page.insert_text((420, y), "Unit Price", fontsize=11, fontname="helv")
    page.insert_text((500, y), "Amount", fontsize=11, fontname="helv")
    page.draw_line((50, y + 6), (562, y + 6))

    # Line items
    items = [
        ("Enterprise PDF Processing Cluster", "2", "$1,250.00", "$2,500.00"),
        ("Audit Trail & Compliance Storage (1 TB)", "1", "$450.00", "$450.00"),
        ("Dedicated Support SLA", "1", "$300.00", "$300.00"),
    ]
    y += 28
    for desc, qty, unit, amt in items:
        page.insert_text((50, y), desc, fontsize=10, fontname="helv")
        page.insert_text((355, y), qty, fontsize=10, fontname="helv")
        page.insert_text((425, y), unit, fontsize=10, fontname="helv")
        page.insert_text((500, y), amt, fontsize=10, fontname="helv")
        y += 22

    # Totals
    page.draw_line((350, y + 10), (562, y + 10))
    page.insert_text((400, y + 32), "Subtotal:", fontsize=11, fontname="helv")
    page.insert_text((500, y + 32), "$3,250.00", fontsize=11, fontname="helv")
    page.insert_text((400, y + 52), "Tax (8.5%):", fontsize=11, fontname="helv")
    page.insert_text((500, y + 52), "$276.25", fontsize=11, fontname="helv")
    page.insert_text((400, y + 76), "Total Due:", fontsize=13, fontname="helv")
    page.insert_text((495, y + 76), "$3,526.25", fontsize=13, fontname="helv")

    # Payment terms footer
    page.insert_text(
        (50, 700),
        "Payment Terms: Net 30. Please reference INV-2026-0842 on wire transfers.",
        fontsize=9,
        fontname="helv",
    )

    doc.save(pdf_path)
    doc.close()
    return pdf_path


def normalize_bbox(bbox: tuple[float, float, float, float], width: float, height: float) -> list[float]:
    x1, y1, x2, y2 = bbox
    return [
        round(x1 / width, 4),
        round(y1 / height, 4),
        round(x2 / width, 4),
        round(y2 / height, 4),
    ]


def extract_pdf_with_provenance(pdf_path: Path, annotate_dir: Path | None = None) -> dict:
    doc = pymupdf.open(pdf_path)
    pages_data = []
    extracted_fields = []

    field_patterns = {
        "invoice_number": re.compile(r"Invoice No:\s*([A-Z0-9-]+)", re.IGNORECASE),
        "issue_date": re.compile(r"Issue Date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
        "due_date": re.compile(r"Due Date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
        "total_due": re.compile(r"Total Due:\s*(\$[\d,]+\.\d{2})", re.IGNORECASE),
        "vendor": re.compile(r"^([A-Z][A-Z0-9\s]+INC\.?)$"),
    }

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        width = page.rect.width
        height = page.rect.height

        words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
        is_digital = len(words) > 0

        text_dict = page.get_text("dict")
        lines_out = []

        for b_idx, block in enumerate(text_dict.get("blocks", [])):
            if block.get("type") != 0:  # 0 = text block
                continue
            for l_idx, line in enumerate(block.get("lines", [])):
                line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                if not line_text:
                    continue
                bbox = tuple(line["bbox"])
                line_id = f"p{page_num}_b{b_idx}_l{l_idx}"
                line_entry = {
                    "id": line_id,
                    "text": line_text,
                    "bbox": [round(v, 2) for v in bbox],
                    "norm_bbox": normalize_bbox(bbox, width, height),
                }
                lines_out.append(line_entry)

                # Anchor extracted fields to exact line bounding boxes
                for field_name, pattern in field_patterns.items():
                    match = pattern.search(line_text)
                    if match:
                        extracted_fields.append({
                            "field": field_name,
                            "value": match.group(1).strip(),
                            "confidence": 0.99,
                            "page": page_num,
                            "source_id": line_id,
                            "bbox": line_entry["bbox"],
                            "norm_bbox": line_entry["norm_bbox"],
                        })

        # Fallback for split-column label -> value on the same horizontal row
        found_fields = {f["field"] for f in extracted_fields if f["page"] == page_num}
        if "total_due" not in found_fields:
            for label_line in lines_out:
                if re.search(r"Total Due:", label_line["text"], re.IGNORECASE):
                    ly0, ly1 = label_line["bbox"][1], label_line["bbox"][3]
                    lx1 = label_line["bbox"][2]
                    for val_line in lines_out:
                        vy0, vy1 = val_line["bbox"][1], val_line["bbox"][3]
                        vx0 = val_line["bbox"][0]
                        if abs(ly0 - vy0) < 6 and vx0 > lx1 and re.match(r"^\$[\d,]+\.\d{2}$", val_line["text"]):
                            extracted_fields.append({
                                "field": "total_due",
                                "value": val_line["text"],
                                "confidence": 0.98,
                                "page": page_num,
                                "source_id": val_line["id"],
                                "bbox": val_line["bbox"],
                                "norm_bbox": val_line["norm_bbox"],
                            })
                            break

        pages_data.append({
            "page": page_num,
            "width": width,
            "height": height,
            "is_digital": is_digital,
            "word_count": len(words),
            "line_count": len(lines_out),
            "lines": lines_out,
        })

        # Render annotated preview PNG if requested
        if annotate_dir is not None:
            annotate_dir.mkdir(parents=True, exist_ok=True)
            page_fields = [f for f in extracted_fields if f["page"] == page_num]
            for f in page_fields:
                rect = pymupdf.Rect(f["bbox"])
                page.draw_rect(rect, color=(0.1, 0.45, 0.95), fill=(0.1, 0.45, 0.95), fill_opacity=0.15, width=1.5)
                page.insert_text((rect.x0, max(10, rect.y0 - 3)), f["field"], fontsize=7, color=(0.1, 0.35, 0.85))
            pix = page.get_pixmap(dpi=150)
            pix.save(annotate_dir / f"annotated_page_{page_num}.png")

    doc.close()
    return {
        "file": str(pdf_path),
        "total_pages": len(pages_data),
        "extracted_fields": extracted_fields,
        "pages": pages_data,
    }


def main():
    parser = argparse.ArgumentParser(description="DocTrace PyMuPDF extraction test")
    parser.add_argument("pdf", nargs="?", help="Path to a PDF file (creates a sample digital PDF if omitted)")
    parser.add_argument("--out", default="output/result.json", help="Output JSON path")
    parser.add_argument("--annotate-dir", default="output", help="Directory to save annotated PNGs")
    args = parser.parse_args()

    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        pdf_path = create_sample_invoice_pdf(Path("sample_invoice.pdf"))
        print(f"Generated sample digital PDF: {pdf_path}")

    result = extract_pdf_with_provenance(pdf_path, annotate_dir=Path(args.annotate_dir))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\nProcessed {result['total_pages']} page(s) from {pdf_path}")
    print(f"Saved full JSON output to {out_path}")
    print("\nExtracted Fields with Bounding-Box Provenance:")
    for f in result["extracted_fields"]:
        print(f"  - {f['field']}: {f['value']} (page {f['page']}, bbox={f['bbox']}, norm={f['norm_bbox']})")


if __name__ == "__main__":
    main()
