"""Sends Hatua's emails: verify your email, reset your password, and a CHW's invite.

With SMTP_HOST set, messages go out over SMTP (STARTTLS). Without it nothing is sent:
the message is logged and kept in `outbox`, so links can be read from the server log
during development and from `outbox` in tests.
"""
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("uvicorn.error")


@dataclass
class Sent:
    to: str
    subject: str
    body: str


# Messages not sent over SMTP (development and tests). Newest last, capped.
outbox: list[Sent] = []


def send(to: str, subject: str, body: str) -> None:
    """Never raises: a mail problem must not break sign-up or sign-in."""
    if not settings.smtp_host:
        outbox.append(Sent(to, subject, body))
        del outbox[:-50]
        log.info("EMAIL NOT SENT (SMTP_HOST is empty). To: %s | %s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException):
        log.exception("could not send email to %s", to)


def send_verification(to: str, name: str, link: str) -> None:
    send(to, "Confirm your email for Hatua",
         f"Hello {name},\n\n"
         "Open this link to confirm your email address and finish setting up your Hatua "
         f"account:\n\n{link}\n\n"
         f"The link works for {settings.verify_link_hours} hours. If it runs out, open "
         "Hatua and choose to send the link again. If you did not expect a Hatua "
         "account, you can ignore this message.\n")


def send_password_reset(to: str, name: str, link: str) -> None:
    send(to, "Reset your Hatua password",
         f"Hello {name},\n\n"
         f"Open this link to choose a new password:\n\n{link}\n\n"
         f"The link works for {settings.reset_link_minutes} minutes and only once. If you "
         "did not ask for this, you can ignore this message; your password stays the same.\n")


def send_chw_invite(to: str, name: str, link: str, site: str) -> None:
    send(to, "You are invited to Hatua as a community health worker",
         f"Hello {name},\n\n"
         "An administrator has added you to Hatua as a community health worker. Hatua "
         "helps caregivers check how their young children are developing, and sends the "
         "checks that need a look to their health worker.\n\n"
         "Open this link to set up your account. You will choose a password and add your "
         f"phone number:\n\n{link}\n\n"
         f"Or sign in with Google at {site} using this email address ({to}).\n\n"
         f"The link works for {settings.invite_link_days} days. If it runs out, ask your "
         "administrator to send a new one. If you did not expect this, you can ignore "
         "this message.\n")
