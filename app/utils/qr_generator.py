# app/utils/qr_generator.py

import qrcode
import os

def generate_qr(registration_no: str):
    os.makedirs("uploads/qr", exist_ok=True)

    path = f"uploads/qr/{registration_no}.png"

    qr = qrcode.make(registration_no)
    qr.save(path)

    return path