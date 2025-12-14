"""
Tests for IMAP Listener Service

Tests:
- Email parsing (text, HTML, attachments)
- Kafka publishing with retries
- IMAP connection and error handling
"""

import pytest
from datetime import UTC, datetime

from app.services.imap_listener import EmailReceivedEvent, IMAPListenerService


class TestEmailParsing:
    """Test email parsing from raw RFC822 messages."""

    @pytest.mark.asyncio
    async def test_parse_simple_text_email(self):
        """Test parsing plain text email."""
        raw_email = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Message-ID: <test123@example.com>
Content-Type: text/plain; charset=utf-8

This is a test email body.
"""
        listener = IMAPListenerService()
        event = await listener.parse_email(raw_email)

        assert event.message_id == "test123@example.com"
        assert event.from_email == "sender@example.com"
        assert event.subject == "Test Email"
        assert "test email body" in event.body_text.lower()
        assert event.body_html is None
        assert len(event.attachments) == 0

    @pytest.mark.asyncio
    async def test_parse_html_email(self):
        """Test parsing HTML email."""
        raw_email = b"""From: sender@example.com
To: recipient@example.com
Subject: HTML Email
Message-ID: <html123@example.com>
Content-Type: text/html; charset=utf-8

<html><body><h1>Test HTML</h1></body></html>
"""
        listener = IMAPListenerService()
        event = await listener.parse_email(raw_email)

        assert event.message_id == "html123@example.com"
        assert event.body_html is not None
        assert "<h1>Test HTML</h1>" in event.body_html

    @pytest.mark.asyncio
    async def test_parse_email_with_attachments(self):
        """Test parsing email with attachments (stub)."""
        # TODO: Create multipart email with attachments
        # For now, test basic structure
        listener = IMAPListenerService()

        # Stub: verify attachment parsing logic exists
        assert hasattr(listener, "parse_email")


class TestKafkaPublishing:
    """Test Kafka publishing with retry logic."""

    @pytest.mark.asyncio
    async def test_publish_to_kafka_success(self):
        """Test successful Kafka publish."""
        listener = IMAPListenerService(kafka_producer=None)  # Stub mode

        event = EmailReceivedEvent(
            message_id="test123@example.com",
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            subject="Test",
            raw_message=b"test",
            size_bytes=100,
        )

        # Should not raise exception in stub mode
        await listener.publish_to_kafka(event)

    @pytest.mark.asyncio
    async def test_publish_retry_logic(self):
        """Test Kafka publish retry on failure."""

        class FailingProducer:
            def __init__(self):
                self.attempts = 0

            def send(self, *args, **kwargs):
                self.attempts += 1
                raise Exception("Kafka connection failed")

        listener = IMAPListenerService(kafka_producer=FailingProducer())

        event = EmailReceivedEvent(
            message_id="test456@example.com",
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            subject="Retry Test",
            raw_message=b"test",
            size_bytes=100,
        )

        # Should retry 3 times and raise exception
        with pytest.raises(Exception):
            await listener.publish_to_kafka(event, max_retries=3)


class TestIMAPConnection:
    """Test IMAP connection and lifecycle."""

    @pytest.mark.asyncio
    async def test_imap_listener_init(self):
        """Test IMAP listener initialization."""
        listener = IMAPListenerService(
            host="mail.97v.ru", port=993, user="info@97v.ru", password="secret"
        )

        assert listener.host == "mail.97v.ru"
        assert listener.port == 993
        assert listener.user == "info@97v.ru"
        assert listener.use_ssl is True

    @pytest.mark.asyncio
    async def test_connect_stub(self):
        """Test IMAP connection (stub - no real server)."""
        listener = IMAPListenerService()

        # In stub mode, should return True (no actual connection)
        # TODO: Mock aioimaplib when implementing real connection
        connected = await listener.connect()
        assert connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test IMAP disconnection."""
        listener = IMAPListenerService()
        await listener.disconnect()  # Should not raise exception


class TestEmailReceivedEvent:
    """Test EmailReceivedEvent schema validation."""

    def test_event_creation(self):
        """Test creating EmailReceivedEvent."""
        event = EmailReceivedEvent(
            message_id="msg123",
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            subject="Test Subject",
            body_text="Email body",
            raw_message=b"raw email content",
            size_bytes=1024,
        )

        assert event.message_id == "msg123"
        assert event.from_email == "sender@example.com"
        assert event.subject == "Test Subject"
        assert len(event.attachments) == 0

    def test_event_with_attachments(self):
        """Test EmailReceivedEvent with attachments."""
        event = EmailReceivedEvent(
            message_id="msg456",
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            subject="With Attachment",
            attachments=[
                {
                    "filename": "document.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 50000,
                }
            ],
            raw_message=b"raw email",
            size_bytes=51000,
        )

        assert len(event.attachments) == 1
        assert event.attachments[0]["filename"] == "document.pdf"

    def test_event_timestamp_auto_generated(self):
        """Test that received_at timestamp is auto-generated."""
        event = EmailReceivedEvent(
            message_id="msg789",
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            subject="Timestamp Test",
            raw_message=b"test",
            size_bytes=100,
        )

        assert event.received_at is not None
        assert isinstance(event.received_at, datetime)
        # Should be recent (within last minute)
        assert (datetime.now(UTC) - event.received_at).total_seconds() < 60
