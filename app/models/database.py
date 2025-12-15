"""
Database ORM Models for ERP Integration.

Contains models for:
- InvoiceORM (invoices table)
- OrderORM (orders table)
- TicketORM (tickets table)
- CompanyORM (companies table)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class InvoiceORM(Base):
    """Invoice model for database"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    
    vendor_email = Column(String(255), nullable=False)
    vendor_name = Column(String(255), nullable=True)
    vendor_inn = Column(String(50), nullable=True)
    
    customer_name = Column(String(255), nullable=True)
    customer_inn = Column(String(50), nullable=True)
    
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    
    subtotal_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    vat_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    
    currency = Column(String(3), nullable=False, default='RUB')
    status = Column(String(50), nullable=False, default='pending_approval')
    
    email_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class OrderORM(Base):
    """Purchase Order model for database"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(100), unique=True, nullable=False, index=True)
    
    customer_email = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=True)
    customer_inn = Column(String(50), nullable=True)
    
    supplier_email = Column(String(255), nullable=True)
    supplier_name = Column(String(255), nullable=True)
    
    order_date = Column(DateTime, nullable=False)
    delivery_date = Column(DateTime, nullable=True)
    
    total_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    
    status = Column(String(50), nullable=False, default='pending_approval')
    priority = Column(String(20), nullable=False, default='normal')
    
    line_items_count = Column(Integer, nullable=False, default=0)
    
    email_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class TicketORM(Base):
    """Support Ticket model for database"""
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_number = Column(String(100), unique=True, nullable=False, index=True)
    
    customer_email = Column(String(255), nullable=False)
    
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    priority = Column(String(20), nullable=False, default='normal')
    status = Column(String(50), nullable=False, default='open')
    
    resolution = Column(Text, nullable=True)
    
    email_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class CompanyORM(Base):
    """Company/Supplier model for database"""
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    inn = Column(String(50), nullable=True)
    
    is_trusted = Column(Integer, nullable=False, default=0)  # Boolean as int
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
