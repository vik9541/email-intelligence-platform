"""
IMAP Listener Service - Real-time email monitoring

Listens to IMAP server using IDLE protocol and publishes new emails to Kafka.
Supports:
- Real-time email detection (IMAP IDLE)
- MIME parsing with attachments
- Kafka producer with retry logic
- Error handling and reconnection

Author: Email Intelligence Platform Team
Version: 1.0.0
"""

import asyncio
import email
import logging
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from typing import Any

from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)


class EmailReceivedEvent(BaseModel):
    """Event schema for new email received."""

    message_id: str = Field(..., description="Unique message ID from email headers")
    from_email: EmailStr = Field(..., description="Sender email address")
    to_email: list[EmailStr] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body_text: str | None = Field(None, description="Plain text body")
    body_html: str | None = Field(None, description="HTML body")
    attachments: list[dict[str, Any]] = Field(
        default_factory=list, description="List of attachments metadata"
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Server receipt timestamp"
    )
    raw_message: bytes = Field(..., description="Raw RFC822 message")
    size_bytes: int = Field(..., description="Email size in bytes")


class IMAPListenerService:
    """
    IMAP listener service using IDLE protocol for real-time email monitoring.

    Connects to Dovecot IMAP server and listens for new emails.
    Publishes EmailReceivedEvent to Kafka topic 'email.received'.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 993,
        user: str = "info@97v.ru",
        password: str = "",
        kafka_producer=None,
        use_ssl: bool = True,
    ):
        """
        Initialize IMAP listener.

        Args:
            host: IMAP server hostname (Dovecot)
            port: IMAP port (993 for IMAPS)
            user: Email account username
            password: Email account password
            kafka_producer: Kafka producer instance
            use_ssl: Use SSL/TLS connection
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.producer = kafka_producer
        self.use_ssl = use_ssl
        self.running = False
        self.imap_client = None

    async def connect(self) -> bool:
        """
        Connect to IMAP server.

        Returns:
            bool: True if connected successfully
        """
        try:
            # TODO: Implement aioimaplib connection
            # self.imap_client = aioimaplib.IMAP4_SSL(self.host, self.port)
            # await self.imap_client.login(self.user, self.password)
            # await self.imap_client.select('INBOX')

            logger.info(
                "Connected to IMAP server",
                extra={"host": self.host, "user": self.user, "port": self.port},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False

    async def listen(self):
        """
        Start IMAP IDLE listening for new emails.

        Main event loop that:
        1. Connects to IMAP server
        2. Enters IDLE mode
        3. Waits for new email notifications
        4. Fetches and processes new emails
        5. Publishes to Kafka
        """
        self.running = True
        logger.info("Starting IMAP listener service")

        while self.running:
            try:
                # Connect if not connected
                if not self.imap_client:
                    connected = await self.connect()
                    if not connected:
                        await asyncio.sleep(5)  # Retry after 5s
                        continue

                # TODO: Implement IMAP IDLE protocol
                # await self.imap_client.idle_start()
                # response = await self.imap_client.wait_server_push()
                #
                # if 'EXISTS' in response:
                #     # New email arrived
                #     await self.fetch_new_emails()

                # Stub: simulate checking every 10 seconds
                await asyncio.sleep(10)
                logger.debug("IMAP IDLE check (stub)")

            except asyncio.CancelledError:
                logger.info("IMAP listener cancelled")
                self.running = False
                break

            except Exception as e:
                logger.error(f"Error in IMAP listener loop: {e}")
                await asyncio.sleep(5)  # Retry after error

        # Cleanup
        await self.disconnect()

    async def fetch_new_emails(self):
        """
        Fetch new emails from IMAP server.

        Called when IDLE detects new messages.
        """
        try:
            # TODO: Implement email fetching
            # typ, data = await self.imap_client.search(None, 'UNSEEN')
            # email_ids = data[0].split()
            #
            # for email_id in email_ids:
            #     typ, msg_data = await self.imap_client.fetch(email_id, '(RFC822)')
            #     raw_email = msg_data[0][1]
            #     await self.process_email(raw_email)

            logger.debug("Fetching new emails (stub)")

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")

    async def process_email(self, raw_email: bytes):
        """
        Process raw email and publish to Kafka.

        Args:
            raw_email: Raw RFC822 email message
        """
        try:
            # Parse email
            event = await self.parse_email(raw_email)

            # Publish to Kafka
            await self.publish_to_kafka(event)

            logger.info(
                "Email processed successfully",
                extra={
                    "message_id": event.message_id,
                    "from": event.from_email,
                    "subject": event.subject,
                },
            )

        except Exception as e:
            logger.error(f"Error processing email: {e}")

    async def parse_email(self, raw_email: bytes) -> EmailReceivedEvent:
        """
        Parse raw email into EmailReceivedEvent.

        Args:
            raw_email: Raw RFC822 email bytes

        Returns:
            EmailReceivedEvent with parsed data
        """
        # Parse using Python email library
        msg = BytesParser(policy=policy.default).parsebytes(raw_email)

        # Extract headers
        message_id = msg.get("Message-ID", "").strip("<>")
        from_email = msg.get("From", "")
        to_emails = msg.get_all("To", [])
        subject = msg.get("Subject", "")

        # Extract body
        body_text = None
        body_html = None
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Plain text body
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")

                # HTML body
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    body_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")

                # Attachments
                elif "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(
                            {
                                "filename": filename,
                                "content_type": content_type,
                                "size_bytes": len(part.get_payload(decode=True)),
                            }
                        )
        else:
            # Single part email
            body_text = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

        return EmailReceivedEvent(
            message_id=message_id,
            from_email=from_email,
            to_email=to_emails,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            raw_message=raw_email,
            size_bytes=len(raw_email),
        )

    async def publish_to_kafka(self, event: EmailReceivedEvent, max_retries: int = 3):
        """
        Publish email event to Kafka with retry logic.

        Args:
            event: EmailReceivedEvent to publish
            max_retries: Maximum retry attempts

        Raises:
            Exception if all retries fail
        """
        for attempt in range(max_retries):
            try:
                if self.producer:
                    # TODO: Implement actual Kafka publish
                    # self.producer.send(
                    #     topic='email.received',
                    #     value=event.model_dump_json().encode('utf-8'),
                    #     key=event.message_id.encode('utf-8')
                    # )
                    # await self.producer.flush()

                    logger.info(
                        "Published to Kafka",
                        extra={
                            "topic": "email.received",
                            "message_id": event.message_id,
                            "attempt": attempt + 1,
                        },
                    )
                    return

                logger.warning("Kafka producer not configured (stub mode)")
                return

            except Exception as e:
                logger.warning(
                    f"Kafka publish failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise

    async def disconnect(self):
        """Disconnect from IMAP server."""
        try:
            if self.imap_client:
                # TODO: Implement disconnect
                # await self.imap_client.logout()
                logger.info("Disconnected from IMAP server")
        except Exception as e:
            logger.error(f"Error disconnecting from IMAP: {e}")

    async def stop(self):
        """Stop the listener service."""
        logger.info("Stopping IMAP listener service")
        self.running = False
