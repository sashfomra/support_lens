"""
Email IMAP Scraper — ingests unread support emails as tickets.
Works with Gmail, Outlook, and any IMAP-compatible mail server.
No third-party libraries needed — uses Python's built-in imaplib.

Setup for Gmail:
  1. Enable 2-factor auth on your Google account
  2. Create an App Password: myaccount.google.com/apppasswords
  3. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in backend/.env
  4. Set IMAP_HOST=imap.gmail.com (default)

Setup for Outlook:
  IMAP_HOST=outlook.office365.com
"""
import imaplib
import email
import logging
import os
import re
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")


def _decode_header_value(value: str) -> str:
    """Safely decode an email header."""
    try:
        parts = decode_header(value)
        decoded = []
        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return "".join(decoded)
    except Exception:
        return str(value)


def _get_email_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


def fetch_unread_emails(max_emails: int = 20) -> List[Dict]:
    """
    Connect to the configured IMAP server and fetch unread emails.
    Returns a list of email dicts ready to be turned into tickets.
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.warning("Email scraper: EMAIL_ADDRESS or EMAIL_APP_PASSWORD not set in .env")
        return []

    emails = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("INBOX")

        # Search for unread emails
        _, ids = mail.search(None, "UNSEEN")
        email_ids = ids[0].split()

        # Process most recent first, limited
        for eid in reversed(email_ids[-max_emails:]):
            try:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_header_value(msg.get("Subject", "Support Request"))
                from_raw = msg.get("From", "unknown@unknown.com")
                sender_name = re.sub(r"<.*?>", "", from_raw).strip().strip('"')
                sender_email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", from_raw)
                sender_email = sender_email_match.group(0) if sender_email_match else "unknown@unknown.com"
                body = _get_email_body(msg)

                if not body:
                    continue

                emails.append({
                    "source": "email",
                    "subject": subject[:200],
                    "description": body[:2000],
                    "customer_name": sender_name or sender_email,
                    "customer_email": sender_email,
                    "customer_tier": "standard",
                    "message_id": msg.get("Message-ID", str(eid)),
                })

                # Mark as read
                mail.store(eid, "+FLAGS", "\\Seen")

            except Exception as e:
                logger.error(f"Error processing email {eid}: {e}")
                continue

        mail.logout()
        logger.info(f"Email scraper: fetched {len(emails)} unread emails")

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP login failed: {e}. Check EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env")
    except Exception as e:
        logger.error(f"Email scraper error: {e}")

    return emails


def ingest_emails_to_db(emails_list: List[Dict]) -> int:
    """Insert fetched emails as tickets into the SupportLens database."""
    if not emails_list:
        return 0

    from database import SessionLocal, Ticket
    from ai.pipeline import detect_emotion, detect_intent, detect_churn_risk, compute_urgency_score

    db = SessionLocal()
    created = 0
    now = datetime.utcnow()

    try:
        for e in emails_list:
            # Check for duplicate by message_id
            existing = db.query(Ticket).filter(
                Ticket.external_id == e.get("message_id")
            ).first()
            if existing:
                continue

            emotion_type, emotion_score = detect_emotion(e["description"])
            intent = detect_intent(e["description"])
            churn = detect_churn_risk(e["description"])
            severity = "P1" if emotion_score >= 8 or churn else "P2"
            sla_h = 4 if severity == "P1" else 12

            urgency = compute_urgency_score(
                emotion_score=emotion_score,
                emotion_type=emotion_type,
                is_churn_risk=churn,
                customer_tier="standard",
                intent=intent,
                sla_hours_remaining=sla_h,
                keyword_severity=severity,
            )

            ticket = Ticket(
                external_id=e.get("message_id"),
                subject=e["subject"],
                description=e["description"],
                customer_name=e["customer_name"],
                customer_email=e["customer_email"],
                customer_tier=e["customer_tier"],
                source="email",
                status="open",
                emotion_type=emotion_type,
                emotion_score=emotion_score,
                intent=intent,
                urgency_score=urgency,
                is_churn_risk=churn,
                is_escalated=churn or emotion_score >= 8,
                requires_human=churn or emotion_score >= 8,
                severity=severity,
                sla_deadline=now + timedelta(hours=sla_h),
                sla_breached=False,
                product_area="Email",
                platform="Web",
                created_at=now,
                updated_at=now,
            )
            db.add(ticket)
            created += 1

        db.commit()
        logger.info(f"Email scraper: inserted {created} tickets from emails")
    except Exception as ex:
        db.rollback()
        logger.error(f"Email DB insert error: {ex}")
    finally:
        db.close()

    return created
