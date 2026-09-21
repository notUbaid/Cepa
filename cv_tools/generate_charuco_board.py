"""
ChArUco Calibration Board Generator

Generates a print-ready ChArUco calibration board matching the exact
system configuration in backend/config.py:
  - 7x5 squares (squares_x=7, squares_y=5)
  - 40mm square length
  - 20mm marker length
  - DICT_4X4_250 dictionary

Usage:
  python cv_tools/generate_charuco_board.py
"""
import sys
from pathlib import Path
import cv2
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image

# Output directory
OUT_DIR = Path(__file__).parent / "calibration_board"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SQUARES_X = 7
SQUARES_Y = 5
SQUARE_LENGTH_MM = 40.0
MARKER_LENGTH_MM = 20.0
DICT_TYPE = cv2.aruco.DICT_4X4_250


def generate_charuco_png(dpi: int = 300) -> Path:
    """
    Generate high-resolution PNG of the ChArUco board.
    At 300 DPI, 1 mm ≈ 11.811 pixels.
    """
    pixels_per_mm = dpi / 25.4
    board_w_px = int(SQUARES_X * SQUARE_LENGTH_MM * pixels_per_mm)
    board_h_px = int(SQUARES_Y * SQUARE_LENGTH_MM * pixels_per_mm)

    aruco_dict = cv2.aruco.getPredefinedDictionary(DICT_TYPE)
    board = cv2.aruco.CharucoBoard(
        size=(SQUARES_X, SQUARES_Y),
        squareLength=SQUARE_LENGTH_MM / 1000.0,
        markerLength=MARKER_LENGTH_MM / 1000.0,
        dictionary=aruco_dict,
    )

    board_img = board.generateImage((board_w_px, board_h_px), marginSize=20, borderBits=1)

    png_path = OUT_DIR / "charuco_board_7x5_40mm.png"
    cv2.imwrite(str(png_path), board_img)
    print(f"Generated ChArUco PNG: {png_path} ({board_w_px}x{board_h_px} px)")
    return png_path


def generate_charuco_pdf(png_path: Path) -> Path:
    """
    Generate a 1:1 true-scale printable A4 PDF with calibration ruler and instructions.
    """
    pdf_path = OUT_DIR / "charuco_board_7x5_40mm_A4_printable.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_w, page_h = A4

    # Title & Instructions
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, page_h - 25 * mm, "CEPA SYSTEM — CHARUCO CALIBRATION BOARD")

    c.setFont("Helvetica", 9)
    instructions = [
        "PRINT INSTRUCTIONS:",
        "1. In your printer dialog, select 'Actual Size' or 'Page Scaling: None' (100% scale). DO NOT FIT TO PAGE.",
        "2. Mount or print on rigid, flat cardboard or paperboard.",
        "3. VERIFICATION: Use a physical ruler to measure one checkerboard square. It MUST measure EXACTLY 40.0 mm.",
        "4. Place this board inside the camera frame alongside the onion spread during inspection.",
    ]
    y = page_h - 32 * mm
    for line in instructions:
        c.drawString(20 * mm, y, line)
        y -= 4.5 * mm

    # Draw ChArUco image centered
    board_w_mm = SQUARES_X * SQUARE_LENGTH_MM  # 280 mm might exceed A4 width (210mm)?
    # Wait! A4 width is 210mm, height is 297mm.
    # In portrait, 280mm is too wide. In landscape (297mm x 210mm), 280mm fits!
    # Let's orient as landscape if 7x5=280x200mm.
    c.save()

    # Recreate in Landscape A4 (297mm x 210mm)
    from reportlab.lib.pagesizes import landscape
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    page_w, page_h = landscape(A4)  # 297mm x 210mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 12 * mm, "CEPA SYSTEM — CHARUCO CALIBRATION BOARD (7x5, 40mm Squares, 20mm Markers)")

    c.setFont("Helvetica", 8)
    c.drawString(
        15 * mm,
        page_h - 17 * mm,
        "PRINT INSTRUCTION: Print at 100% ('Actual Size'). Measure any square with a ruler: it must equal EXACTLY 40 mm.",
    )

    # Calculate centered position for board image
    board_w_pt = SQUARES_X * SQUARE_LENGTH_MM * mm
    board_h_pt = SQUARES_Y * SQUARE_LENGTH_MM * mm
    board_x = (page_w - board_w_pt) / 2
    board_y = 10 * mm

    c.drawImage(str(png_path), board_x, board_y, width=board_w_pt, height=board_h_pt)

    # Draw 50mm verification ruler on the side
    ruler_x = 15 * mm
    ruler_y = page_h - 22 * mm
    c.line(ruler_x, ruler_y, ruler_x + 50 * mm, ruler_y)
    c.line(ruler_x, ruler_y - 2 * mm, ruler_x, ruler_y + 2 * mm)
    c.line(ruler_x + 50 * mm, ruler_y - 2 * mm, ruler_x + 50 * mm, ruler_y + 2 * mm)
    c.drawString(ruler_x + 10 * mm, ruler_y + 2 * mm, "<- 50.0 mm Verification Line ->")

    c.showPage()
    c.save()
    print(f"Generated printable true-scale PDF: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    png = generate_charuco_png()
    pdf = generate_charuco_pdf(png)
    print("Calibration board generation complete.")
