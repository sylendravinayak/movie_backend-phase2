from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Any, Dict, Optional

from utils.config import Settings

settings = Settings()


class EmailService:
    def __init__(self) -> None:
        # Uses app/templates by default
        template_dir = Path(__file__).resolve().parents[1] / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,
        )

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        tpl = self.jinja_env.get_template(template_name)
        return tpl.render(**context)

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not settings.SMTP_HOST or not settings.SMTP_PORT:
            print("⚠ SMTP host/port not configured")
            return False
        if not (settings.SMTP_USER and settings.SMTP_PASSWORD):
            print("⚠ SMTP credentials not configured")
            return False

        from_addr = settings.SMTP_FROM or settings.SMTP_USER

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = from_addr
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_content, "html"))

            # STARTTLS on 587 by default
            server = smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT))
            try:
                server.ehlo()
                server.starttls()
                server.ehlo()
            except Exception:
                # If using port 465 or server doesn’t support STARTTLS, ignore
                pass

            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"❌ Email failed: {type(e).__name__}: {e}")
            return False

    async def send_payment_success_email(
        self,
        to_email: str,
        user_name: str,
        payment_id: str,
        booking_id: str,
        amount: float,
        payment_method: str,
        transaction_id: str,
        payment_date: str,
        deeplink: Optional[str] = None,
    ) -> bool:
        html = self.render(
            "notification.html",
            dict(
                user_name=user_name,
                type="payment_success",
                title="Payment Successful",
                message=f"Payment of ₹{amount:.2f} received for booking {booking_id}",
                metadata={
                    "paymentId": payment_id,
                    "bookingId": booking_id,
                    "amount": amount,
                    "paymentMethod": payment_method,
                    "transactionId": transaction_id,
                    "paymentDate": payment_date,
                },
                frontend_url=settings.FRONTEND_URL,
                deeplink=deeplink,
            ),
        )
        return await self.send_email(to_email, f"✅ Payment Successful - ₹{amount:.2f}", html)

    async def send_booking_confirmed_email(
        self,
        to_email: str,
        user_name: str,
        booking_id: str,
        movie_title: str,
        show_datetime: str,
        total_amount: float,
        deeplink: Optional[str] = None,
    ) -> bool:
        html = self.render(
            "notification.html",
            dict(
                user_name=user_name,
                type="booking_confirmed",
                title="Booking Confirmed",
                message=f"Your booking for {movie_title} has been confirmed",
                metadata={
                    "bookingId": booking_id,
                    "movieTitle": movie_title,
                    "showDateTime": show_datetime,
                    "totalAmount": total_amount,
                },
                frontend_url=settings.FRONTEND_URL,
                deeplink=deeplink,
            ),
        )
        return await self.send_email(to_email, f"🎉 Booking Confirmed - {booking_id}", html)

    async def send_payment_failed_email(
        self,
        to_email: str,
        user_name: str,
        booking_id: str,
        amount: float,
        reason: str,
        deeplink: Optional[str] = None,
    ) -> bool:
        html = self.render(
            "notification.html",
            dict(
                user_name=user_name,
                type="payment_failed",
                title="Payment Failed",
                message=f"Payment of ₹{amount:.2f} failed. Reason: {reason}",
                metadata={"bookingId": booking_id, "amount": amount, "reason": reason},
                frontend_url=settings.FRONTEND_URL,
                deeplink=deeplink,
            ),
        )
        return await self.send_email(to_email, f"❌ Payment Failed - {booking_id}", html)

    async def send_booking_cancelled_email(
        self,
        to_email: str,
        user_name: str,
        booking_id: str,
        refund_amount: float,
        cancellation_reason: str,
        deeplink: Optional[str] = None,
    ) -> bool:
        html = self.render(
            "notification.html",
            dict(
                user_name=user_name,
                type="booking_cancelled",
                title="Booking Cancelled",
                message=f"Booking {booking_id} cancelled. Refund: ₹{refund_amount:.2f}",
                metadata={
                    "bookingId": booking_id,
                    "refundAmount": refund_amount,
                    "reason": cancellation_reason,
                },
                frontend_url=settings.FRONTEND_URL,
                deeplink=deeplink,
            ),
        )
        return await self.send_email(to_email, f"⚠ Booking Cancelled - {booking_id}", html)