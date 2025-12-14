"""ERPActionExecutor - execute ERP actions based on email analysis."""

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.erp_client import ERPClient, ERPClientError
from app.models.email import Email
from app.models.email_actions import EmailAction
from app.schemas.erp_schemas import ActionResult, ActionStatus, OrderItem

logger = logging.getLogger(__name__)


class OrderParsingError(Exception):
    """Order parsing error."""

    pass


class ERPActionExecutor:
    """
    ERP action executor based on email analysis results.

    Supported actions:
    - create_order: create order from email
    - update_invoice: update invoice status
    - create_ticket: create support ticket
    """

    def __init__(
        self,
        erp_client: ERPClient,
        db_session: AsyncSession,
    ) -> None:
        self.erp_client = erp_client
        self.db_session = db_session

    async def create_order(
        self,
        action: EmailAction,
        email: Email,
        context: dict[str, Any],
    ) -> ActionResult:
        """Create order in ERP based on email data."""
        logger.info(
            "Starting create_order action",
            extra={"email_id": email.id, "action_id": action.id},
        )

        action.mark_executing()
        await self.db_session.flush()

        try:
            items = await self._parse_order_items(email, context)

            if not items:
                error_msg = "Could not parse order items"
                logger.error(
                    error_msg,
                    extra={"email_id": email.id, "action_id": action.id},
                )
                action.mark_failed(error_msg)
                await self.db_session.commit()
                return ActionResult(
                    status=ActionStatus.FAILED,
                    error=error_msg,
                )

            logger.info(
                f"Parsed {len(items)} order items",
                extra={"email_id": email.id, "items_count": len(items)},
            )

            customer_id = context.get("customer_id")
            if not customer_id:
                error_msg = "customer_id not found in context"
                logger.error(error_msg, extra={"email_id": email.id})
                action.mark_failed(error_msg)
                await self.db_session.commit()
                return ActionResult(
                    status=ActionStatus.FAILED,
                    error=error_msg,
                )

            if isinstance(customer_id, str):
                customer_id = UUID(customer_id)

            order = await self.erp_client.create_order(
                customer_id=customer_id,
                items=items,
                source="email",
                source_email_id=email.id,
            )

            action.mark_completed(
                erp_entity_type="Order",
                erp_entity_id=order.id,
            )
            action.actionpayload = {
                "order_number": order.number,
                "items_count": len(items),
                "total_amount": str(order.total_amount),
            }
            await self.db_session.commit()

            logger.info(
                "Order created successfully",
                extra={
                    "email_id": email.id,
                    "order_id": str(order.id),
                    "order_number": order.number,
                },
            )

            return ActionResult(
                status=ActionStatus.SUCCESS,
                erp_entity_id=order.id,
                message=f"Order {order.number} created with {len(items)} items",
            )

        except ERPClientError as e:
            error_msg = str(e)
            logger.error(f"ERP client error: {error_msg}", extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg, extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

    async def _parse_order_items(
        self,
        email: Email,
        context: dict[str, Any],
    ) -> list[OrderItem]:
        """Parse order items from email and attachments."""
        items: list[OrderItem] = []

        text = getattr(email, "body", "") or getattr(email, "text", "") or ""
        if text:
            text_items = self._parse_from_text(text)
            items.extend(text_items)

        attachments = context.get("attachments", [])
        for attachment in attachments:
            filename = attachment.get("filename", "").lower()
            content = attachment.get("content")

            if not content:
                continue

            if filename.endswith((".xlsx", ".xls", ".csv")):
                excel_items = self._parse_from_excel(content, filename)
                items.extend(excel_items)
            elif filename.endswith(".pdf"):
                pdf_items = self._parse_from_pdf(content)
                items.extend(pdf_items)

        return items

    def _parse_from_text(self, text: str) -> list[OrderItem]:
        """Parse order items from email text."""
        items: list[OrderItem] = []

        # Pattern 1: "Code: SKU-123, Quantity: 10, Price: 100.00"
        pattern1 = re.compile(
            r"(?:kod|code|artikul|sku)[:\s]+([A-Za-z0-9\-_]+)"
            r"[,;\s]+"
            r"(?:kol-vo|kolichestvo|qty|quantity)[:\s]+(\d+(?:[.,]\d+)?)"
            r"(?:[,;\s]+(?:cena|price)[:\s]+(\d+(?:[.,]\d+)?))?",
            re.IGNORECASE,
        )

        for match in pattern1.finditer(text):
            try:
                productcode = match.group(1).strip()
                quantity = Decimal(match.group(2).replace(",", "."))
                unitprice = None
                if match.group(3):
                    unitprice = Decimal(match.group(3).replace(",", "."))
                unit = "pcs"

                items.append(
                    OrderItem(
                        productcode=productcode,
                        description="",
                        quantity=quantity,
                        unitprice=unitprice,
                        unit=unit,
                    )
                )
            except (InvalidOperation, ValueError):
                continue

        # Pattern 2: "SKU-123 - 10 pcs - 100.00"
        pattern2 = re.compile(
            r"([A-Za-z]{2,5}[\-_]?\d{3,10})"
            r"\s*[-]\s*"
            r"(\d+(?:[.,]\d+)?)\s*(?:pcs|ea)?"
            r"(?:\s*[-]\s*(\d+(?:[.,]\d+)?)\s*)?",
            re.IGNORECASE,
        )

        for match in pattern2.finditer(text):
            try:
                productcode = match.group(1).strip()
                if any(item.productcode == productcode for item in items):
                    continue

                quantity = Decimal(match.group(2).replace(",", "."))
                unitprice = None
                if match.group(3):
                    unitprice = Decimal(match.group(3).replace(",", "."))

                items.append(
                    OrderItem(
                        productcode=productcode,
                        description="",
                        quantity=quantity,
                        unitprice=unitprice,
                        unit="pcs",
                    )
                )
            except (InvalidOperation, ValueError):
                continue

        # Pattern 3: Simple tabular format
        lines = text.split("\n")
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                potential_code = parts[0]
                if re.match(r"^[A-Za-z]{1,5}[\-_]?\d{2,10}$", potential_code):
                    if any(item.productcode == potential_code for item in items):
                        continue

                    try:
                        quantity = Decimal(parts[1].replace(",", "."))
                        unitprice = None
                        if len(parts) >= 3:
                            try:
                                unitprice = Decimal(parts[2].replace(",", "."))
                            except InvalidOperation:
                                pass

                        items.append(
                            OrderItem(
                                productcode=potential_code,
                                description="",
                                quantity=quantity,
                                unitprice=unitprice,
                                unit="pcs",
                            )
                        )
                    except (InvalidOperation, ValueError):
                        continue

        return items

    def _parse_from_excel(
        self,
        content: bytes,
        filename: str,
    ) -> list[OrderItem]:
        """Parse order items from Excel/CSV file (stub)."""
        logger.info(f"Parsing Excel/CSV file: {filename} (stub)")
        return []

    def _parse_from_pdf(self, content: bytes) -> list[OrderItem]:
        """Parse order items from PDF file (stub)."""
        logger.info("Parsing PDF file (stub)")
        return []

    async def update_invoice(
        self,
        action: EmailAction,
        email: Email,
        context: dict[str, Any],
    ) -> ActionResult:
        """Update invoice status in ERP based on email analysis."""
        logger.info(
            "Starting update_invoice action",
            extra={"email_id": email.id, "action_id": action.id},
        )

        action.mark_executing()
        await self.db_session.flush()

        try:
            invoice_id = context.get("invoice_id")
            if not invoice_id:
                if action.actionpayload:
                    invoice_id = action.actionpayload.get("invoice_id")

            if not invoice_id:
                error_msg = "invoice_id not found in context or action_payload"
                logger.error(error_msg, extra={"email_id": email.id})
                action.mark_failed(error_msg)
                await self.db_session.commit()
                return ActionResult(
                    status=ActionStatus.FAILED,
                    error=error_msg,
                )

            if isinstance(invoice_id, str):
                invoice_id = UUID(invoice_id)

            email_text = getattr(email, "body", "") or getattr(email, "text", "") or ""
            status = self._determine_invoice_status(email_text)
            notes = self._extract_invoice_notes(email)

            invoice = await self.erp_client.update_invoice(
                invoice_id=invoice_id,
                status=status,
                notes=notes,
            )

            action.mark_completed(
                erp_entity_type="Invoice",
                erp_entity_id=invoice.id,
            )
            action.actionpayload = {
                "invoice_number": invoice.number,
                "status": status,
                "notes": notes[:200] if notes else None,
            }
            await self.db_session.commit()

            logger.info(
                "Invoice updated successfully",
                extra={
                    "email_id": email.id,
                    "invoice_id": str(invoice.id),
                    "status": status,
                },
            )

            return ActionResult(
                status=ActionStatus.SUCCESS,
                erp_entity_id=invoice.id,
                message=f"Invoice {invoice.number} updated to {status}",
            )

        except ERPClientError as e:
            error_msg = str(e)
            logger.error(f"ERP client error: {error_msg}", extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg, extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

    def _determine_invoice_status(self, text: str) -> str:
        """Determine invoice status from email text analysis."""
        text_lower = text.lower()

        paid_keywords = ["paid", "payment received", "payment confirmed"]
        cancelled_keywords = ["cancel", "annul", "void"]
        overdue_keywords = ["overdue", "past due"]
        pending_keywords = ["pending", "in progress"]

        for keyword in paid_keywords:
            if keyword in text_lower:
                return "paid"
        for keyword in cancelled_keywords:
            if keyword in text_lower:
                return "cancelled"
        for keyword in overdue_keywords:
            if keyword in text_lower:
                return "overdue"
        for keyword in pending_keywords:
            if keyword in text_lower:
                return "pending"

        return "pending"

    def _extract_invoice_notes(self, email: Email) -> str:
        """Extract brief summary from email for invoice notes."""
        subject = getattr(email, "subject", "") or ""
        body = getattr(email, "body", "") or getattr(email, "text", "") or ""
        summary = body[:200].strip()
        if len(body) > 200:
            summary += "..."
        return f"From email: {subject}. {summary}"

    async def create_ticket(
        self,
        action: EmailAction,
        email: Email,
        context: dict[str, Any],
    ) -> ActionResult:
        """Create support ticket based on email."""
        logger.info(
            "Starting create_ticket action",
            extra={"email_id": email.id, "action_id": action.id},
        )

        action.mark_executing()
        await self.db_session.flush()

        try:
            customer_id = context.get("customer_id")
            if not customer_id:
                error_msg = "customer_id not found in context"
                logger.error(error_msg, extra={"email_id": email.id})
                action.mark_failed(error_msg)
                await self.db_session.commit()
                return ActionResult(
                    status=ActionStatus.FAILED,
                    error=error_msg,
                )

            if isinstance(customer_id, str):
                customer_id = UUID(customer_id)

            subject = getattr(email, "subject", "") or "Support Request"
            body = getattr(email, "body", "") or getattr(email, "text", "") or ""
            description = self._extract_ticket_description(body)
            priority = self._determine_ticket_priority(email, body)

            ticket = await self.erp_client.create_ticket(
                subject=subject,
                description=description,
                customer_id=customer_id,
                priority=priority,
                source_email_id=email.id,
            )

            action.mark_completed(
                erp_entity_type="Ticket",
                erp_entity_id=ticket.id,
            )
            action.actionpayload = {
                "ticket_number": ticket.number,
                "subject": subject[:100],
                "priority": priority,
            }
            await self.db_session.commit()

            logger.info(
                "Ticket created successfully",
                extra={
                    "email_id": email.id,
                    "ticket_id": str(ticket.id),
                    "ticket_number": ticket.number,
                    "priority": priority,
                },
            )

            return ActionResult(
                status=ActionStatus.SUCCESS,
                erp_entity_id=ticket.id,
                message=f"Ticket {ticket.number} created with priority {priority}",
            )

        except ERPClientError as e:
            error_msg = str(e)
            logger.error(f"ERP client error: {error_msg}", extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg, extra={"email_id": email.id})
            action.mark_failed(error_msg)
            await self.db_session.commit()
            return ActionResult(status=ActionStatus.FAILED, error=error_msg)

    def _extract_ticket_description(self, body: str) -> str:
        """Extract description for ticket from email body."""
        if not body:
            return ""
        paragraphs = body.strip().split("\n\n")
        first_paragraph = paragraphs[0] if paragraphs else body
        if len(first_paragraph) <= 500:
            return first_paragraph.strip()
        return first_paragraph[:500].strip() + "..."

    def _determine_ticket_priority(self, email: Email, body: str) -> int:
        """Determine ticket priority (1=low, 2=medium, 3=high)."""
        text_lower = body.lower()
        subject_lower = (getattr(email, "subject", "") or "").lower()
        combined = text_lower + " " + subject_lower

        email_priority = getattr(email, "priority", None)
        if email_priority is not None:
            if email_priority > 7:
                return 3
            elif email_priority >= 4:
                return 2

        critical_keywords = ["critical", "emergency", "urgent", "asap", "immediately"]
        high_keywords = ["important", "high priority"]
        low_keywords = ["low priority", "when possible"]

        for keyword in critical_keywords:
            if keyword in combined:
                return 3
        for keyword in high_keywords:
            if keyword in combined:
                return 3
        for keyword in low_keywords:
            if keyword in combined:
                return 1

        return 2


async def create_email_action(
    db_session: AsyncSession,
    email_id: int,
    action_type: str,
    payload: dict | None = None,
) -> EmailAction:
    """Create EmailAction record in DB."""
    action = EmailAction(
        emailid=email_id,
        actiontype=action_type,
        actionpayload=payload,
        status="pending",
        retrycount=0,
        createdat=datetime.now(UTC),
    )
    db_session.add(action)
    await db_session.flush()
    await db_session.refresh(action)
    return action
