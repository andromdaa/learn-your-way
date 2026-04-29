"""Generate a minimal PDF fixture for parser unit tests.

Run directly to write tiny_test.pdf next to this script:
    python tests/fixtures/generate_tiny_pdf.py

The output path is not committed; the script is.
"""

from pathlib import Path

from fpdf import FPDF

_HEADING = "Introduction"
_BODY = "This section introduces the core concepts."
_HEADING2 = "Conclusion"
_BODY2 = "All concepts have been covered."


def generate(dest: Path) -> None:
    pdf = FPDF()
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, _HEADING, ln=True)

    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, _BODY)
    pdf.ln(4)

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, _HEADING2, ln=True)

    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, _BODY2)

    pdf.output(str(dest))


if __name__ == "__main__":
    out = Path(__file__).parent / "tiny_test.pdf"
    generate(out)
    print(f"written: {out}")
