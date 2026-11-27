# DocTrace — Auditable PDF Extraction & Source Annotation Engine

**DocTrace** bridges the gap between automated document extraction and human-in-the-loop verification. Built for high-stakes business documents—including **contracts, invoices, MSAs, credit agreements, and operational records**—it maps every extracted data point directly back to its exact visual coordinates on the source PDF.

### Why DocTrace?
When reviewing extracted data from complex business documents, trusting raw JSON or spreadsheet outputs isn't enough. Reviewers need instant proof of provenance. DocTrace renders interactive bounding-box annotations over the original document so reviewers can click any extracted field and immediately see where it came from.

### Key Features
* **Visual Source Provenance:** Maps extracted key-value pairs, line items, and clauses to exact page numbers and bounding-box coordinates (`[x1, y1, x2, y2]`).
* **Multi-Document Support:** Handles structured, semi-structured, and unstructured layouts across invoices, purchase orders, legal agreements, and operational statements.
* **Side-by-Side Review UI:** Synchronized split-screen view linking extracted data fields to highlighted PDF regions with auto-scroll and zoom.
* **Confidence & Audit Trail:** Flags low-confidence extractions and logs reviewer approvals or overrides for compliance and auditability.
* **Schema-Agnostic Output:** Exports validated data alongside coordinate metadata in clean JSON or CSV formats.
