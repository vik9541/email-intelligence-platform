"""Tests for ERPActionExecutor."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.integrations.erp_client import ERPClient, ERPClientError, ERPValidationError
from app.models.email import Email
from app.models.email_actions import EmailAction
from app.schemas.erp_schemas import ActionStatus, ERPOrder, OrderItem, OrderStatus
from app.services.erp_action_executor import ERPActionExecutor, create_email_action

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def customer_id() -> UUID:
    """Customer UUID fixture."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_email() -> Email:
    """Test email with order items fixture."""
    email = Email()
    email.id = 42
    email.subject = "Order Request"
    email.sender = "customer@example.com"
    email.recipient = "orders@company.com"
    email.body = """
    Hello!

    Please create an order:

    Code: SKU-12345, Quantity: 10, Price: 1500.00
    Code: ART-98765, Quantity: 5, Price: 2500.50

    Best regards,
    Customer
    """
    email.received_at = datetime.now(tz=None)
    email.created_at = datetime.now(tz=None)
    return email


@pytest.fixture
def email_without_items() -> Email:
    """Email without order items fixture."""
    email = Email()
    email.id = 43
    email.subject = "Question about delivery"
    email.sender = "customer@example.com"
    email.recipient = "support@company.com"
    email.body = "Hello! When will my order be delivered?"
    email.received_at = datetime.now(tz=None)
    email.created_at = datetime.now(tz=None)
    return email


@pytest.fixture
def sample_action() -> EmailAction:
    """Test action fixture."""
    action = EmailAction()
    action.id = 1
    action.emailid = 42
    action.actiontype = "createorder"
    action.status = "pending"
    action.retrycount = 0
    action.createdat = datetime.now(tz=None)
    return action


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock DB session fixture."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_erp_client() -> AsyncMock:
    """Mock ERP client fixture."""
    client = AsyncMock(spec=ERPClient)
    return client


@pytest.fixture
def erp_order(customer_id: UUID) -> ERPOrder:
    """Test ERP order fixture."""
    return ERPOrder(
        id=uuid4(),
        number="ORD-000042-0001",
        status=OrderStatus.DRAFT,
        customer_id=customer_id,
        items=[
            OrderItem(
                productcode="SKU-12345",
                description="",
                quantity=Decimal("10"),
                unitprice=Decimal("1500.00"),
                unit="pcs",
            ),
            OrderItem(
                productcode="ART-98765",
                description="",
                quantity=Decimal("5"),
                unitprice=Decimal("2500.50"),
                unit="pcs",
            ),
        ],
        total_amount=Decimal("27502.50"),
        source="email",
        source_email_id=42,
    )


# ============================================================================
# Tests: Success scenario
# ============================================================================


class TestERPActionExecutorSuccess:
    """Tests for successful scenarios."""

    @pytest.mark.asyncio
    async def test_create_order_success(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
        erp_order: ERPOrder,
    ) -> None:
        """Test successful order creation."""
        # Arrange
        mock_erp_client.create_order.return_value = erp_order
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        # Act
        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        # Assert
        assert result.status == ActionStatus.SUCCESS
        assert result.erp_entity_id == erp_order.id
        assert "ORD-000042-0001" in result.message

        # Check ERP client was called
        mock_erp_client.create_order.assert_called_once()
        call_kwargs = mock_erp_client.create_order.call_args.kwargs
        assert call_kwargs["customer_id"] == customer_id
        assert call_kwargs["source"] == "email"
        assert call_kwargs["source_email_id"] == sample_email.id
        assert len(call_kwargs["items"]) == 2

        # Check action was updated
        assert sample_action.status == "completed"
        assert sample_action.erpentitytype == "Order"
        assert sample_action.erpentityid == erp_order.id

        # Check commit was called
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_order_parses_items_correctly(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
        erp_order: ERPOrder,
    ) -> None:
        """Test that order items are parsed correctly."""
        mock_erp_client.create_order.return_value = erp_order
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        # Check parsed items
        call_kwargs = mock_erp_client.create_order.call_args.kwargs
        items = call_kwargs["items"]

        assert len(items) == 2

        # First item
        assert items[0].productcode == "SKU-12345"
        assert items[0].quantity == Decimal("10")
        assert items[0].unitprice == Decimal("1500.00")

        # Second item
        assert items[1].productcode == "ART-98765"
        assert items[1].quantity == Decimal("5")
        assert items[1].unitprice == Decimal("2500.50")

    @pytest.mark.asyncio
    async def test_create_order_with_string_customer_id(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
        erp_order: ERPOrder,
    ) -> None:
        """Test order creation with string customer_id."""
        mock_erp_client.create_order.return_value = erp_order
        context = {"customer_id": str(customer_id)}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        assert result.status == ActionStatus.SUCCESS


# ============================================================================
# Tests: Parsing errors
# ============================================================================


class TestERPActionExecutorParsingErrors:
    """Tests for parsing error scenarios."""

    @pytest.mark.asyncio
    async def test_create_order_no_items_parsed(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        email_without_items: Email,
        sample_action: EmailAction,
        customer_id: UUID,
    ) -> None:
        """Test order creation when no items can be parsed."""
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=email_without_items,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "Could not parse order items" in result.error

        # Check action was marked as failed
        assert sample_action.status == "failed"
        assert "Could not parse order items" in sample_action.errormessage

    @pytest.mark.asyncio
    async def test_create_order_missing_customer_id(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
    ) -> None:
        """Test order creation without customer_id."""
        context: dict[str, Any] = {}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "customer_id not found" in result.error


# ============================================================================
# Tests: ERP errors
# ============================================================================


class TestERPActionExecutorERPErrors:
    """Tests for ERP error scenarios."""

    @pytest.mark.asyncio
    async def test_create_order_erp_client_error(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
    ) -> None:
        """Test order creation when ERP client raises error."""
        mock_erp_client.create_order.side_effect = ERPClientError("Connection failed")
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "Connection failed" in result.error

        # Check action was marked as failed
        assert sample_action.status == "failed"

    @pytest.mark.asyncio
    async def test_create_order_erp_validation_error(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
    ) -> None:
        """Test order creation when ERP validation fails."""
        mock_erp_client.create_order.side_effect = ERPValidationError("Invalid product SKU")
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "Invalid product SKU" in result.error

    @pytest.mark.asyncio
    async def test_create_order_unexpected_exception(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        sample_email: Email,
        sample_action: EmailAction,
        customer_id: UUID,
    ) -> None:
        """Test order creation with unexpected exception."""
        mock_erp_client.create_order.side_effect = RuntimeError("Unexpected error")
        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_order(
            action=sample_action,
            email=sample_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "Unexpected error" in result.error


# ============================================================================
# Tests: Text parsing
# ============================================================================


class TestTextParsing:
    """Tests for text parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_from_text_format1(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test parsing format 'Code: X, Quantity: Y, Price: Z'."""
        email = Email()
        email.id = 1
        email.body = "Code: TEST-001, Quantity: 5, Price: 100.00"

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        items = await executor._parse_order_items(email, {})

        assert len(items) == 1
        assert items[0].productcode == "TEST-001"
        assert items[0].quantity == Decimal("5")
        assert items[0].unitprice == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_parse_from_text_format2(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test parsing format 'SKU-123 - 10 - 100.00'."""
        email = Email()
        email.id = 1
        email.body = "SKU-12345 - 10 - 100.00"

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        items = await executor._parse_order_items(email, {})

        assert len(items) == 1
        assert items[0].productcode == "SKU-12345"
        assert items[0].quantity == Decimal("10")
        assert items[0].unitprice == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_parse_from_text_empty(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test parsing empty text."""
        email = Email()
        email.id = 1
        email.body = ""

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        items = await executor._parse_order_items(email, {})

        assert items == []

    @pytest.mark.asyncio
    async def test_parse_from_text_no_items(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test parsing text without order items."""
        email = Email()
        email.id = 1
        email.body = "Just a regular email without any product codes or orders."

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        items = await executor._parse_order_items(email, {})

        assert items == []


# ============================================================================
# Tests: EmailAction model
# ============================================================================


class TestEmailActionModel:
    """Tests for EmailAction model methods."""

    def test_mark_executing(self) -> None:
        """Test mark_executing method."""
        action = EmailAction()
        action.status = "pending"
        action.retrycount = 0

        action.mark_executing()

        assert action.status == "executing"
        assert action.executedat is not None

    def test_mark_completed(self) -> None:
        """Test mark_completed method."""
        action = EmailAction()
        action.status = "executing"
        action.retrycount = 0
        entity_id = uuid4()

        action.mark_completed(
            erp_entity_type="Order",
            erp_entity_id=entity_id,
        )

        assert action.status == "completed"
        assert action.erpentitytype == "Order"
        assert action.erpentityid == entity_id
        assert action.executedat is not None

    def test_mark_failed(self) -> None:
        """Test mark_failed method."""
        action = EmailAction()
        action.status = "executing"
        action.retrycount = 0

        action.mark_failed("Test error message")

        assert action.status == "failed"
        assert action.errormessage == "Test error message"
        assert action.retrycount == 1

    def test_mark_failed_increments_retry(self) -> None:
        """Test that mark_failed increments retry count."""
        action = EmailAction()
        action.status = "pending"
        action.retrycount = 2

        action.mark_failed("Error")

        assert action.retrycount == 3


# ============================================================================
# Tests: Helper functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    @pytest.mark.asyncio
    async def test_create_email_action(
        self,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test create_email_action helper."""
        mock_db_session.refresh = AsyncMock()

        action = await create_email_action(
            db_session=mock_db_session,
            email_id=42,
            action_type="createorder",
            payload={"test": "data"},
        )

        assert action.emailid == 42
        assert action.actiontype == "createorder"
        assert action.actionpayload == {"test": "data"}
        assert action.status == "pending"
        assert action.retrycount == 0

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()


# ============================================================================
# Tests: ERP Client
# ============================================================================


class TestERPClient:
    """Tests for ERPClient."""

    @pytest.mark.asyncio
    async def test_create_order_stub(
        self,
        customer_id: UUID,
    ) -> None:
        """Test ERPClient.create_order stub implementation."""
        from app.integrations.erp_client import ERPClient

        client = ERPClient(base_url="http://test", api_key="key")

        order = await client.create_order(
            customer_id=customer_id,
            items=[
                OrderItem(
                    productcode="TEST-001",
                    description="Test Product",
                    quantity=Decimal("1"),
                    unitprice=Decimal("100"),
                    unit="pcs",
                ),
            ],
            source="email",
            source_email_id=1,
        )

        assert order.customer_id == customer_id
        assert order.status == OrderStatus.DRAFT
        assert order.source == "email"

    @pytest.mark.asyncio
    async def test_create_order_empty_items_raises(
        self,
        customer_id: UUID,
    ) -> None:
        """Test that empty items list raises validation error."""
        from app.integrations.erp_client import ERPClient

        client = ERPClient(base_url="http://test", api_key="key")

        with pytest.raises(ERPValidationError) as exc_info:
            await client.create_order(
                customer_id=customer_id,
                items=[],
                source="email",
                source_email_id=1,
            )

        assert "Order must have at least one item" in str(exc_info.value)


# ============================================================================
# Tests: Update Invoice
# ============================================================================


class TestUpdateInvoice:
    """Tests for update_invoice functionality."""

    @pytest.fixture
    def invoice_email(self) -> Email:
        """Email about invoice payment fixture."""
        email = Email()
        email.id = 50
        email.subject = "Payment Confirmation"
        email.sender = "customer@example.com"
        email.recipient = "accounting@company.com"
        email.body = "Hello! Payment received and confirmed and confirmed. Invoice INV-001 is paid."
        email.received_at = datetime.now(tz=None)
        email.created_at = datetime.now(tz=None)
        return email

    @pytest.fixture
    def invoice_action(self) -> EmailAction:
        """Invoice update action fixture."""
        action = EmailAction()
        action.id = 10
        action.emailid = 50
        action.actiontype = "updateinvoice"
        action.status = "pending"
        action.retrycount = 0
        action.createdat = datetime.now(tz=None)
        return action

    @pytest.mark.asyncio
    async def test_update_invoice_success(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        invoice_email: Email,
        invoice_action: EmailAction,
    ) -> None:
        """Test successful invoice update."""
        from app.schemas.erp_schemas import ERPInvoice, InvoiceStatus

        invoice_id = uuid4()
        mock_invoice = ERPInvoice(
            id=invoice_id,
            number="INV-001",
            status=InvoiceStatus.PAID,
            customer_id=uuid4(),
            amount=Decimal("1000.00"),
        )
        mock_erp_client.update_invoice.return_value = mock_invoice

        context = {"invoice_id": invoice_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.update_invoice(
            action=invoice_action,
            email=invoice_email,
            context=context,
        )

        assert result.status == ActionStatus.SUCCESS
        assert result.erp_entity_id == invoice_id
        assert "INV-001" in result.message
        assert invoice_action.status == "completed"

    @pytest.mark.asyncio
    async def test_update_invoice_missing_id(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        invoice_email: Email,
        invoice_action: EmailAction,
    ) -> None:
        """Test invoice update without invoice_id."""
        context: dict[str, Any] = {}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.update_invoice(
            action=invoice_action,
            email=invoice_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "invoice_id not found" in result.error

    @pytest.mark.asyncio
    async def test_update_invoice_erp_error(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        invoice_email: Email,
        invoice_action: EmailAction,
    ) -> None:
        """Test invoice update with ERP error."""
        mock_erp_client.update_invoice.side_effect = ERPClientError("Invoice not found")

        context = {"invoice_id": uuid4()}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.update_invoice(
            action=invoice_action,
            email=invoice_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "Invoice not found" in result.error

    @pytest.mark.asyncio
    async def test_determine_invoice_status_paid(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test invoice status detection - paid."""
        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        status = executor._determine_invoice_status("Payment received and confirmed")
        assert status == "paid"

    @pytest.mark.asyncio
    async def test_determine_invoice_status_cancelled(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test invoice status detection - cancelled."""
        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        status = executor._determine_invoice_status("Please cancel this invoice")
        assert status == "cancelled"


# ============================================================================
# Tests: Create Ticket
# ============================================================================


class TestCreateTicket:
    """Tests for create_ticket functionality."""

    @pytest.fixture
    def ticket_email(self) -> Email:
        """Support ticket email fixture."""
        email = Email()
        email.id = 60
        email.subject = "Urgent: System not working"
        email.sender = "customer@example.com"
        email.recipient = "support@company.com"
        email.body = "Hello! The system is completely down and we need immediate help. This is critical for our business!"
        email.received_at = datetime.now(tz=None)
        email.created_at = datetime.now(tz=None)
        return email

    @pytest.fixture
    def ticket_action(self) -> EmailAction:
        """Ticket creation action fixture."""
        action = EmailAction()
        action.id = 20
        action.emailid = 60
        action.actiontype = "createticket"
        action.status = "pending"
        action.retrycount = 0
        action.createdat = datetime.now(tz=None)
        return action

    @pytest.mark.asyncio
    async def test_create_ticket_success(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        ticket_email: Email,
        ticket_action: EmailAction,
        customer_id: UUID,
    ) -> None:
        """Test successful ticket creation."""
        from app.schemas.erp_schemas import ERPTicket, TicketStatus

        ticket_id = uuid4()
        mock_ticket = ERPTicket(
            id=ticket_id,
            number="TKT-001",
            subject="Urgent: System not working",
            description="Test description",
            status=TicketStatus.OPEN,
            priority=3,
            customer_id=customer_id,
        )
        mock_erp_client.create_ticket.return_value = mock_ticket

        context = {"customer_id": customer_id}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_ticket(
            action=ticket_action,
            email=ticket_email,
            context=context,
        )

        assert result.status == ActionStatus.SUCCESS
        assert result.erp_entity_id == ticket_id
        assert ticket_action.status == "completed"

    @pytest.mark.asyncio
    async def test_create_ticket_priority_high(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test high priority detection for urgent email."""
        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        email = Email()
        email.subject = "URGENT: Need help ASAP"
        body = "This is critical, please respond immediately!"

        priority = executor._determine_ticket_priority(email, body)
        assert priority == 3

    @pytest.mark.asyncio
    async def test_create_ticket_priority_low(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test low priority detection."""
        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        email = Email()
        email.subject = "Question"
        body = "Low priority request, when possible please help me."

        priority = executor._determine_ticket_priority(email, body)
        assert priority == 1

    @pytest.mark.asyncio
    async def test_create_ticket_missing_customer_id(
        self,
        mock_erp_client: AsyncMock,
        mock_db_session: AsyncMock,
        ticket_email: Email,
        ticket_action: EmailAction,
    ) -> None:
        """Test ticket creation without customer_id."""
        context: dict[str, Any] = {}

        executor = ERPActionExecutor(
            erp_client=mock_erp_client,
            db_session=mock_db_session,
        )

        result = await executor.create_ticket(
            action=ticket_action,
            email=ticket_email,
            context=context,
        )

        assert result.status == ActionStatus.FAILED
        assert "customer_id not found" in result.error
