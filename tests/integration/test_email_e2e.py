"""
End-to-End Integration Tests

Tests complete email pipeline from IMAP to ERP.
"""

import pytest
from datetime import UTC, datetime

from app.services.email_classifier import EmailCategory, EmailClassifierService
from app.services.imap_listener import EmailReceivedEvent
from app.api.email_pipelines import EmailPipelineService


class TestEmailE2EFlow:
    """Test end-to-end email processing flow."""

    @pytest.mark.asyncio
    async def test_invoice_email_full_pipeline(self):
        """Test invoice email through complete pipeline."""
        # Setup services
        classifier = EmailClassifierService()
        # erp_executor = ERPActionExecutor() # TODO: Mock ERP
        pipeline = EmailPipelineService(classifier=classifier, erp_executor=None)

        # Simulate email received event
        email_event = EmailReceivedEvent(
            message_id="inv-test-001@example.com",
            from_email="billing@vendor.com",
            to_email=["info@97v.ru"],
            subject="Invoice INV-123456 - Payment Due",
            body_text="""
            Dear Customer,
            
            Please find attached invoice INV-123456.
            Total amount: $1,234.56
            Payment due: 2025-12-31
            
            Best regards,
            Billing Team
            """,
            raw_message=b"test",
            size_bytes=1024,
        )

        # Process through pipeline
        result = await pipeline.process(email_event)

        # Verify result
        assert result["status"] == "success"
        assert result["classification"].category == EmailCategory.INVOICE
        assert result["classification"].confidence >= 0.85
        assert result["latency_ms"] < 1000  # P95 SLA: < 1s

    @pytest.mark.asyncio
    async def test_purchase_order_full_pipeline(self):
        """Test PO email creates order in ERP."""
        classifier = EmailClassifierService()
        pipeline = EmailPipelineService(classifier=classifier, erp_executor=None)

        email_event = EmailReceivedEvent(
            message_id="po-test-002@example.com",
            from_email="procurement@customer.com",
            to_email=["sales@97v.ru"],
            subject="PO-98765 - Order Confirmation",
            body_text="""
            Purchase Order: PO-98765
            
            Items:
            - Widget A x 100 units
            - Widget B x 50 units
            
            Ship to: 123 Main St, City
            Delivery date: 2025-12-25
            """,
            raw_message=b"test",
            size_bytes=2048,
        )

        result = await pipeline.process(email_event)

        assert result["status"] == "success"
        assert result["classification"].category == EmailCategory.PURCHASE_ORDER
        assert result["classification"].requires_erp_action is True
        # TODO: Verify order created in ERP when integrated

    @pytest.mark.asyncio
    async def test_support_request_pipeline(self):
        """Test support request is classified but no ERP action."""
        classifier = EmailClassifierService()
        pipeline = EmailPipelineService(classifier=classifier, erp_executor=None)

        email_event = EmailReceivedEvent(
            message_id="support-test-003@example.com",
            from_email="customer@example.com",
            to_email=["support@97v.ru"],
            subject="Help - Order Issue",
            body_text="""
            Hi Support,
            
            I have a problem with my recent order.
            Can you help me track it?
            
            Thanks
            """,
            raw_message=b"test",
            size_bytes=512,
        )

        result = await pipeline.process(email_event)

        assert result["status"] == "success"
        assert result["classification"].category == EmailCategory.SUPPORT_REQUEST
        assert result["classification"].requires_erp_action is False

    @pytest.mark.asyncio
    async def test_pipeline_latency_sla(self):
        """Test pipeline meets latency SLA (P95 < 1s)."""
        classifier = EmailClassifierService()
        pipeline = EmailPipelineService(classifier=classifier, erp_executor=None)

        latencies = []

        # Process 20 emails
        for i in range(20):
            email_event = EmailReceivedEvent(
                message_id=f"test-{i}@example.com",
                from_email="sender@example.com",
                to_email=["info@97v.ru"],
                subject=f"Test Email {i}",
                body_text="Test email body",
                raw_message=b"test",
                size_bytes=256,
            )

            result = await pipeline.process(email_event)
            latencies.append(result["latency_ms"])

        # Check P95 < 1000ms
        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]

        assert p95_latency < 1000, f"P95 latency {p95_latency}ms exceeds SLA of 1000ms"

    @pytest.mark.asyncio
    async def test_pipeline_throughput(self):
        """Test pipeline can handle target throughput."""
        import asyncio
        import time

        classifier = EmailClassifierService()
        pipeline = EmailPipelineService(classifier=classifier, erp_executor=None)

        # Target: 10,000 emails/day = ~7 emails/second
        # Test: Process 50 emails and measure time

        start = time.time()

        tasks = []
        for i in range(50):
            email_event = EmailReceivedEvent(
                message_id=f"throughput-{i}@example.com",
                from_email="sender@example.com",
                to_email=["info@97v.ru"],
                subject=f"Test {i}",
                body_text="Test",
                raw_message=b"test",
                size_bytes=100,
            )
            tasks.append(pipeline.process(email_event))

        results = await asyncio.gather(*tasks)
        duration = time.time() - start

        # Calculate emails/second
        emails_per_second = 50 / duration

        # Should handle at least 7 emails/second
        assert (
            emails_per_second >= 7
        ), f"Throughput {emails_per_second:.1f}/s below target 7/s"

        # All should succeed
        assert all(r["status"] == "success" for r in results)


class TestPipelineHealthCheck:
    """Test pipeline health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test pipeline health check."""
        from app.api.email_pipelines import EmailPipelineHealthCheck

        health = await EmailPipelineHealthCheck.check_pipeline_health()

        assert health["status"] == "healthy"
        assert "components" in health
        assert "metrics" in health
        assert "sla" in health

        # Verify SLA targets
        assert health["sla"]["p95_target_ms"] == 1000
        assert health["sla"]["p99_target_ms"] == 2000
        assert health["sla"]["uptime_target_pct"] == 99.9
