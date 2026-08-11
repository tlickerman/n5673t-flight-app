"""
Generates a printable PDF of the completed Flight Assessment Form.
Uses xhtml2pdf (pure-Python, no system dependencies) rendering a Jinja2
HTML template — easy to deploy on Render without native library headaches.
"""

import io
from xhtml2pdf import pisa
from flask import render_template


def generate_pdf(form_data, wb_result, risk_result, weather_data, departure_weather=None, destination_taf=None):
    html = render_template(
        "pdf_report.html",
        form=form_data,
        wb=wb_result,
        risk=risk_result,
        weather=weather_data,
        departure_weather=departure_weather or {},
        destination_taf=destination_taf,
    )
    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer)
    if result.err:
        raise RuntimeError("PDF generation failed")
    buffer.seek(0)
    return buffer
