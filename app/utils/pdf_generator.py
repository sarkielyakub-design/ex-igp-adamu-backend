# app/utils/pdf_generator.py

from reportlab.pdfgen import canvas
import os

def generate_id_card(volunteer):
    os.makedirs("uploads/cards", exist_ok=True)

    pdf_path = f"uploads/cards/{volunteer.registration_no}.pdf"

    pdf = canvas.Canvas(pdf_path)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(150, 800, "EX-IGP ADAMU YOUTH VOLUNTEERS")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, 740, f"Registration No: {volunteer.registration_no}")
    pdf.drawString(50, 720, f"Name: {volunteer.name}")
    pdf.drawString(50, 700, f"Phone: {volunteer.phone}")
    pdf.drawString(50, 680, f"LGA: {volunteer.lga}")

    pdf.save()

    return pdf_path