import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFICATION_EMAIL

def send_reservation_email(data: Dict[str, Any], req_id: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        print("[EMAIL] SMTP_USER o SMTP_PASS no configurados en .env. Se omite el envío del correo.")
        return False

    recipient = NOTIFICATION_EMAIL or SMTP_USER

    subject = f"Nueva Solicitud de Reserva - Radicado #{req_id}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
        .card {{ background: #ffffff; max-width: 580px; margin: 0 auto; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 5px solid #0056b3; }}
        .header {{ background: #0056b3; color: #ffffff; padding: 20px; text-align: center; }}
        .header h2 {{ margin: 0; font-size: 22px; }}
        .content {{ padding: 25px; color: #333333; }}
        .field {{ margin-bottom: 12px; font-size: 15px; border-bottom: 1px solid #edf0f2; padding-bottom: 8px; }}
        .label {{ font-weight: bold; color: #495057; display: inline-block; width: 140px; }}
        .badge {{ background: #e7f1ff; color: #0056b3; padding: 4px 10px; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; font-size: 12px; color: #888888; padding: 15px; background: #f8f9fa; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h2>Horizon Travel Group - Solicitud de Reserva</h2>
        </div>
        <div class="content">
          <p>Se ha generado una nueva solicitud desde el Chatbot:</p>
          <div class="field"><span class="label">Radicado:</span> <span class="badge">{req_id}</span></div>
          <div class="field"><span class="label">Cliente:</span> {data.get('customer_name', 'No especificado')}</div>
          <div class="field"><span class="label">Teléfono:</span> {data.get('customer_phone', 'No especificado')}</div>
          <div class="field"><span class="label">Correo:</span> {data.get('customer_email', 'No especificado')}</div>
          <div class="field"><span class="label">Servicio:</span> {data.get('service_type', 'No especificado')}</div>
          <div class="field"><span class="label">Destino:</span> {data.get('destination', 'No especificado')}</div>
          <div class="field"><span class="label">Fecha:</span> {data.get('travel_date', 'No especificado')}</div>
          <div class="field"><span class="label">Pasajeros:</span> {data.get('passengers', 1)}</div>
        </div>
        <div class="footer">
          Mensaje generado automáticamente por el sistema de reservas de Nexus Travel Bot.
        </div>
      </div>
    </body>
    </html>
    """

    text_content = (
        f"Nueva Solicitud de Reserva - Radicado #{req_id}\n\n"
        f"• Cliente: {data.get('customer_name')}\n"
        f"• Teléfono: {data.get('customer_phone')}\n"
        f"• Correo: {data.get('customer_email')}\n"
        f"• Servicio: {data.get('service_type')}\n"
        f"• Destino: {data.get('destination')}\n"
        f"• Fecha: {data.get('travel_date')}\n"
        f"• Pasajeros: {data.get('passengers')}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = recipient

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        print(f"[EMAIL] Conectando a {SMTP_HOST}:{SMTP_PORT} para enviar a {recipient}...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [recipient], msg.as_string())
        server.quit()
        print(f"[EMAIL] ¡Correo de reserva {req_id} enviado exitosamente a {recipient}!")
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando correo de reserva: {e}")
        return False

