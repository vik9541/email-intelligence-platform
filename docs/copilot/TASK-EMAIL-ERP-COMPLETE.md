# 📋 ПОЛНОЕ ТЕХНИЧЕСКОЕ ЗАДАНИЕ: Email Intelligence Platform

> **Версия:** 1.0.0  
> **Дата:** 15 декабря 2025 г.  
> **Статус:** Production Ready  
> **Тип:** Backend Service + Database Schema + API  

---

## 📖 ОГЛАВЛЕНИЕ

1. [Архитектура системы](#архитектура-системы)
2. [PostgreSQL Schema](#postgresql-schema)
3. [Pydantic Models](#pydantic-models)
4. [EmailParserService](#emailparserservice)
5. [DatabaseService](#databaseservice)
6. [FastAPI Application](#fastapi-application)
7. [Unit Tests](#unit-tests)
8. [Integration Tests](#integration-tests)
9. [Docker Deployment](#docker-deployment)
10. [Мониторинг и Metrics](#мониторинг-и-metrics)

---

## 🏗️ АРХИТЕКТУРА СИСТЕМЫ

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Email Intelligence Platform             │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  IMAP Server │─────▶│ Kafka Queue  │─────▶│ Email Service│
│  (External)  │      │              │      │   (FastAPI)  │
└──────────────┘      └──────────────┘      └──────────────┘
                                                    │
                                                    ▼
                      ┌──────────────────────────────────────┐
                      │       PostgreSQL Database            │
                      │  ┌────────────┐  ┌────────────┐     │
                      │  │  emails    │  │ contacts   │     │
                      │  └────────────┘  └────────────┘     │
                      │  ┌────────────┐  ┌────────────┐     │
                      │  │attachments │  │ threads    │     │
                      │  └────────────┘  └────────────┘     │
                      └──────────────────────────────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────────────────┐
                      │         LLM Classification            │
                      │      (Ollama + Llama 3.1)            │
                      └──────────────────────────────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────────────────┐
                      │          ERP System                   │
                      │    (Auto-actions based on intent)    │
                      └──────────────────────────────────────┘
```

### Компоненты

1. **Email Parser** - Асинхронный парсер MIME email
2. **Database Layer** - SQLAlchemy 2.0 ORM + async PostgreSQL
3. **API Layer** - FastAPI с 6 endpoints
4. **Classification Engine** - LLM-based intent detection
5. **Monitoring** - Prometheus metrics + Grafana dashboards

---

## 🗄️ POSTGRESQL SCHEMA

### Таблица 1: `emails`

**Назначение:** Хранение parsed email писем

```sql
CREATE TABLE emails (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- IMAP Metadata
    message_id VARCHAR(255) UNIQUE NOT NULL,  -- IMAP Message-ID header
    imap_uid BIGINT,                          -- IMAP UID
    imap_folder VARCHAR(100) DEFAULT 'INBOX',
    
    -- Email Headers
    from_address VARCHAR(255) NOT NULL,
    from_name VARCHAR(255),
    to_addresses TEXT[] NOT NULL,             -- Array of recipients
    cc_addresses TEXT[],
    bcc_addresses TEXT[],
    reply_to VARCHAR(255),
    
    -- Content
    subject TEXT,
    body_text TEXT,                           -- Plain text version
    body_html TEXT,                           -- HTML version
    
    -- Threading
    thread_id UUID REFERENCES threads(id) ON DELETE SET NULL,
    in_reply_to VARCHAR(255),                 -- Message-ID of parent email
    references TEXT[],                        -- Array of Message-IDs
    
    -- Classification (populated by LLM)
    intent VARCHAR(50),                       -- 'invoice', 'order', 'complaint', etc.
    sentiment VARCHAR(20),                    -- 'positive', 'neutral', 'negative'
    priority VARCHAR(20) DEFAULT 'normal',    -- 'low', 'normal', 'high', 'urgent'
    confidence_score NUMERIC(3, 2),           -- 0.00 to 1.00
    
    -- ERP Integration
    erp_entity_type VARCHAR(50),              -- 'customer', 'order', 'invoice'
    erp_entity_id VARCHAR(100),               -- ID in external ERP system
    erp_action_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    erp_action_result JSONB,                  -- Details of ERP action
    
    -- Metadata
    size_bytes INTEGER,
    has_attachments BOOLEAN DEFAULT FALSE,
    attachment_count INTEGER DEFAULT 0,
    flags TEXT[],                             -- IMAP flags: ['seen', 'flagged', etc.]
    
    -- Timestamps
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    classified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_emails_message_id ON emails(message_id);
CREATE INDEX idx_emails_from_address ON emails(from_address);
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX idx_emails_intent ON emails(intent) WHERE intent IS NOT NULL;
CREATE INDEX idx_emails_erp_status ON emails(erp_action_status);
CREATE INDEX idx_emails_has_attachments ON emails(has_attachments) WHERE has_attachments = TRUE;

-- Full-text search
CREATE INDEX idx_emails_subject_fts ON emails USING gin(to_tsvector('russian', subject));
CREATE INDEX idx_emails_body_fts ON emails USING gin(to_tsvector('russian', body_text));

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

### Таблица 2: `attachments`

**Назначение:** Хранение метаданных вложений (файлы хранятся в S3)

```sql
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- File Info
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),                -- 'application/pdf', 'image/jpeg', etc.
    size_bytes INTEGER NOT NULL,
    md5_hash VARCHAR(32),                     -- For deduplication
    
    -- Storage
    s3_bucket VARCHAR(100),
    s3_key VARCHAR(500),                      -- S3 object key
    s3_url TEXT,                              -- Pre-signed URL (expires)
    
    -- Metadata
    is_inline BOOLEAN DEFAULT FALSE,          -- True if <img src="cid:...">
    content_id VARCHAR(255),                  -- For inline images
    
    -- Virus Scan
    virus_scan_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'clean', 'infected', 'failed'
    virus_scan_result JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_attachments_email_id ON attachments(email_id);
CREATE INDEX idx_attachments_md5_hash ON attachments(md5_hash);
CREATE INDEX idx_attachments_content_type ON attachments(content_type);

-- Trigger
CREATE TRIGGER trg_attachments_updated_at
    BEFORE UPDATE ON attachments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

### Таблица 3: `contacts`

**Назначение:** Хранение контактов из email (auto-populated)

```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Contact Info
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    
    -- Statistics (auto-updated via triggers)
    emails_sent_count INTEGER DEFAULT 0,
    emails_received_count INTEGER DEFAULT 0,
    last_email_at TIMESTAMP WITH TIME ZONE,
    
    -- Classification
    is_customer BOOLEAN DEFAULT FALSE,
    is_supplier BOOLEAN DEFAULT FALSE,
    is_internal BOOLEAN DEFAULT FALSE,
    
    -- ERP Link
    erp_customer_id VARCHAR(100),
    erp_supplier_id VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_is_customer ON contacts(is_customer) WHERE is_customer = TRUE;
CREATE INDEX idx_contacts_erp_customer_id ON contacts(erp_customer_id) WHERE erp_customer_id IS NOT NULL;

-- Trigger
CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

### Таблица 4: `threads`

**Назначение:** Email threads (conversations)

```sql
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Thread Info
    subject TEXT,                             -- Original subject (without Re:, Fwd:)
    participant_emails TEXT[],                -- Unique list of all participants
    
    -- Statistics
    email_count INTEGER DEFAULT 0,
    last_email_at TIMESTAMP WITH TIME ZONE,
    
    -- Classification
    intent VARCHAR(50),                       -- Inherited from first email
    status VARCHAR(20) DEFAULT 'active',      -- 'active', 'resolved', 'archived'
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_threads_last_email_at ON threads(last_email_at DESC);
CREATE INDEX idx_threads_status ON threads(status);

-- Trigger
CREATE TRIGGER trg_threads_updated_at
    BEFORE UPDATE ON threads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

### Таблица 5: `classification_history`

**Назначение:** История LLM classifications для audit trail

```sql
CREATE TABLE classification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Classification Result
    intent VARCHAR(50) NOT NULL,
    sentiment VARCHAR(20),
    priority VARCHAR(20),
    confidence_score NUMERIC(3, 2),
    
    -- LLM Details
    llm_model VARCHAR(50),                    -- 'llama-3.1-8b', 'gpt-4', etc.
    llm_prompt TEXT,                          -- Actual prompt sent to LLM
    llm_response TEXT,                        -- Raw LLM response
    llm_latency_ms INTEGER,                   -- Response time
    
    -- Metadata
    classified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_classification_email_id ON classification_history(email_id);
CREATE INDEX idx_classification_created_at ON classification_history(classified_at DESC);
```

---

### Таблица 6: `erp_actions`

**Назначение:** Лог действий в ERP системе

```sql
CREATE TABLE erp_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Action Details
    action_type VARCHAR(50) NOT NULL,         -- 'create_order', 'update_invoice', etc.
    entity_type VARCHAR(50),                  -- 'order', 'invoice', 'customer'
    entity_id VARCHAR(100),                   -- ID in ERP system
    
    -- Request/Response
    request_payload JSONB,                    -- What we sent to ERP
    response_payload JSONB,                   -- What ERP returned
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'success', 'failed', 'retrying'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_erp_actions_email_id ON erp_actions(email_id);
CREATE INDEX idx_erp_actions_status ON erp_actions(status);
CREATE INDEX idx_erp_actions_entity ON erp_actions(entity_type, entity_id);
```

---

### Таблица 7: `processing_queue`

**Назначение:** Очередь для обработки email (Kafka alternative)

```sql
CREATE TABLE processing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Queue Info
    queue_name VARCHAR(50) NOT NULL,          -- 'parsing', 'classification', 'erp_action'
    priority INTEGER DEFAULT 5,               -- 1 (highest) to 10 (lowest)
    
    -- Processing
    status VARCHAR(20) DEFAULT 'pending',     -- 'pending', 'processing', 'completed', 'failed'
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_queue_status_priority ON processing_queue(status, priority DESC, scheduled_at ASC);
CREATE INDEX idx_queue_email_id ON processing_queue(email_id);

-- Auto-delete completed items after 7 days
CREATE OR REPLACE FUNCTION cleanup_old_queue_items()
RETURNS void AS $$
BEGIN
    DELETE FROM processing_queue
    WHERE status IN ('completed', 'failed')
      AND completed_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
```

---

### Таблица 8: `api_metrics`

**Назначение:** Метрики API для мониторинга

```sql
CREATE TABLE api_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Request Info
    endpoint VARCHAR(100) NOT NULL,           -- '/parse', '/classify', etc.
    method VARCHAR(10) NOT NULL,              -- 'GET', 'POST', etc.
    status_code INTEGER NOT NULL,             -- 200, 400, 500, etc.
    
    -- Performance
    latency_ms INTEGER NOT NULL,
    
    -- User Info (optional)
    client_ip VARCHAR(45),
    user_agent TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX idx_metrics_created_at ON api_metrics(created_at DESC);
CREATE INDEX idx_metrics_status_code ON api_metrics(status_code);

-- Partitioning by month (для production)
-- CREATE TABLE api_metrics_2025_12 PARTITION OF api_metrics FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

---

### Views для аналитики

```sql
-- View 1: Email statistics by sender
CREATE VIEW email_stats_by_sender AS
SELECT
    from_address,
    COUNT(*) AS total_emails,
    COUNT(*) FILTER (WHERE has_attachments = TRUE) AS emails_with_attachments,
    AVG(size_bytes)::INTEGER AS avg_size_bytes,
    MAX(received_at) AS last_email_at,
    ARRAY_AGG(DISTINCT intent) FILTER (WHERE intent IS NOT NULL) AS intents
FROM emails
GROUP BY from_address
ORDER BY total_emails DESC;

-- View 2: Daily email volume
CREATE VIEW email_volume_daily AS
SELECT
    DATE(received_at) AS date,
    COUNT(*) AS total_emails,
    COUNT(*) FILTER (WHERE intent = 'invoice') AS invoices,
    COUNT(*) FILTER (WHERE intent = 'order') AS orders,
    COUNT(*) FILTER (WHERE intent = 'complaint') AS complaints,
    AVG(CASE WHEN classified_at IS NOT NULL THEN EXTRACT(EPOCH FROM (classified_at - received_at)) END)::INTEGER AS avg_classification_time_sec
FROM emails
GROUP BY DATE(received_at)
ORDER BY date DESC;

-- View 3: ERP action success rate
CREATE VIEW erp_action_stats AS
SELECT
    action_type,
    COUNT(*) AS total_actions,
    COUNT(*) FILTER (WHERE status = 'success') AS successful,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
    (COUNT(*) FILTER (WHERE status = 'success')::FLOAT / NULLIF(COUNT(*), 0) * 100)::NUMERIC(5, 2) AS success_rate_pct,
    AVG(EXTRACT(EPOCH FROM (completed_at - executed_at)))::INTEGER AS avg_duration_sec
FROM erp_actions
GROUP BY action_type
ORDER BY total_actions DESC;
```

---

## 🐍 PYDANTIC MODELS

### File: `app/models/email_models.py`

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


# Enums
class EmailIntent(str, Enum):
    INVOICE = "invoice"
    ORDER = "order"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    NEWSLETTER = "newsletter"
    SPAM = "spam"
    OTHER = "other"


class EmailSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EmailPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ERPActionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VirusScanStatus(str, Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    FAILED = "failed"


# Base Models
class AttachmentBase(BaseModel):
    filename: str = Field(..., max_length=255)
    content_type: Optional[str] = Field(None, max_length=100)
    size_bytes: int = Field(..., ge=0)
    md5_hash: Optional[str] = Field(None, max_length=32)
    is_inline: bool = False
    content_id: Optional[str] = None


class AttachmentCreate(AttachmentBase):
    email_id: UUID
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None


class AttachmentDB(AttachmentBase):
    id: UUID
    email_id: UUID
    s3_bucket: Optional[str]
    s3_key: Optional[str]
    s3_url: Optional[str]
    virus_scan_status: VirusScanStatus
    virus_scan_result: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailBase(BaseModel):
    message_id: str = Field(..., max_length=255)
    from_address: EmailStr
    from_name: Optional[str] = Field(None, max_length=255)
    to_addresses: List[EmailStr] = Field(..., min_items=1)
    cc_addresses: Optional[List[EmailStr]] = []
    bcc_addresses: Optional[List[EmailStr]] = []
    reply_to: Optional[EmailStr] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    received_at: datetime
    sent_at: Optional[datetime] = None

    @validator('to_addresses', 'cc_addresses', 'bcc_addresses', pre=True)
    def validate_email_lists(cls, v):
        if v is None:
            return []
        return list(set(v))  # Remove duplicates


class EmailCreate(EmailBase):
    imap_uid: Optional[int] = None
    imap_folder: str = "INBOX"
    in_reply_to: Optional[str] = None
    references: Optional[List[str]] = []
    size_bytes: Optional[int] = None
    flags: Optional[List[str]] = []


class EmailDB(EmailBase):
    id: UUID
    imap_uid: Optional[int]
    imap_folder: str
    thread_id: Optional[UUID]
    in_reply_to: Optional[str]
    references: Optional[List[str]]
    intent: Optional[EmailIntent]
    sentiment: Optional[EmailSentiment]
    priority: EmailPriority
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    erp_entity_type: Optional[str]
    erp_entity_id: Optional[str]
    erp_action_status: ERPActionStatus
    erp_action_result: Optional[dict]
    size_bytes: Optional[int]
    has_attachments: bool
    attachment_count: int
    flags: Optional[List[str]]
    parsed_at: datetime
    classified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailWithAttachments(EmailDB):
    attachments: List[AttachmentDB] = []


# Classification Models
class ClassificationRequest(BaseModel):
    email_id: UUID
    subject: str
    body_text: str
    from_address: EmailStr


class ClassificationResult(BaseModel):
    intent: EmailIntent
    sentiment: EmailSentiment
    priority: EmailPriority
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None  # Explanation from LLM


# API Request/Response Models
class ParseEmailRequest(BaseModel):
    raw_email: bytes = Field(..., description="Raw email in RFC822 format")
    imap_uid: Optional[int] = None
    imap_folder: str = "INBOX"


class ParseEmailResponse(BaseModel):
    email: EmailWithAttachments
    processing_time_ms: int


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    redis: Optional[str] = None
    kafka: Optional[str] = None
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_emails: int
    emails_last_24h: int
    emails_pending_classification: int
    emails_pending_erp_action: int
    avg_classification_time_ms: float
    avg_parse_time_ms: float
```

---

## 🔧 EMAILPARSERSERVICE

### File: `app/services/email_parser.py`

```python
import email
import hashlib
import logging
from email import policy
from email.message import EmailMessage
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError

from app.models.email_models import (
    EmailCreate,
    AttachmentCreate,
    EmailWithAttachments,
)

logger = logging.getLogger(__name__)


class EmailParserService:
    """
    Async email parser для извлечения данных из raw email.
    
    Поддерживает:
    - MIME multipart parsing
    - Извлечение headers (From, To, CC, BCC, Subject, Date, etc.)
    - Парсинг text/plain и text/html body
    - Извлечение вложений
    - Загрузка вложений в S3
    - Обработка inline images (Content-ID)
    """

    def __init__(
        self,
        s3_bucket: str,
        s3_client: Optional[boto3.client] = None,
    ):
        """
        Args:
            s3_bucket: S3 bucket для хранения вложений
            s3_client: boto3 S3 client (если None, создаётся новый)
        """
        self.s3_bucket = s3_bucket
        self.s3_client = s3_client or boto3.client('s3')

    async def parse_email(self, raw_email: bytes) -> EmailWithAttachments:
        """
        Парсит raw email и возвращает structured data.
        
        Args:
            raw_email: Raw email в формате RFC822 (bytes)
            
        Returns:
            EmailWithAttachments object
            
        Raises:
            ValueError: Если email невалидный
            Exception: При других ошибках парсинга
        """
        try:
            start_time = datetime.utcnow()
            
            # Parse email
            msg: EmailMessage = email.message_from_bytes(
                raw_email,
                policy=policy.default
            )
            
            # Extract headers
            headers = self._parse_headers(msg)
            
            # Extract body
            body_text, body_html = self._parse_body(msg)
            
            # Extract attachments
            attachments_data = self._parse_attachments(msg)
            
            # Upload attachments to S3
            attachments = []
            for att_data in attachments_data:
                s3_key = await self._upload_to_s3(
                    att_data['content'],
                    att_data['filename'],
                    att_data['content_type']
                )
                
                attachment = AttachmentCreate(
                    email_id=uuid4(),  # Will be set later
                    filename=att_data['filename'],
                    content_type=att_data['content_type'],
                    size_bytes=len(att_data['content']),
                    md5_hash=hashlib.md5(att_data['content']).hexdigest(),
                    is_inline=att_data.get('is_inline', False),
                    content_id=att_data.get('content_id'),
                    s3_bucket=self.s3_bucket,
                    s3_key=s3_key,
                )
                attachments.append(attachment)
            
            # Create EmailCreate object
            email_obj = EmailCreate(
                message_id=headers['message_id'],
                from_address=headers['from_address'],
                from_name=headers.get('from_name'),
                to_addresses=headers['to_addresses'],
                cc_addresses=headers.get('cc_addresses', []),
                bcc_addresses=headers.get('bcc_addresses', []),
                reply_to=headers.get('reply_to'),
                subject=headers.get('subject'),
                body_text=body_text,
                body_html=body_html,
                received_at=headers['received_at'],
                sent_at=headers.get('sent_at'),
                in_reply_to=headers.get('in_reply_to'),
                references=headers.get('references', []),
                size_bytes=len(raw_email),
                flags=headers.get('flags', []),
            )
            
            parse_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.info(
                f"Parsed email {email_obj.message_id} in {parse_time_ms}ms "
                f"({len(attachments)} attachments)"
            )
            
            return EmailWithAttachments(
                **email_obj.dict(),
                id=uuid4(),
                attachments=attachments,
                has_attachments=len(attachments) > 0,
                attachment_count=len(attachments),
            )
            
        except Exception as e:
            logger.error(f"Failed to parse email: {e}", exc_info=True)
            raise

    def _parse_headers(self, msg: EmailMessage) -> dict:
        """Extract headers from email."""
        headers = {}
        
        # Message-ID
        headers['message_id'] = msg.get('Message-ID', str(uuid4()))
        
        # From
        from_header = msg.get('From', '')
        if '<' in from_header:
            headers['from_name'], from_email = from_header.split('<')
            headers['from_address'] = from_email.strip('>')
            headers['from_name'] = headers['from_name'].strip()
        else:
            headers['from_address'] = from_header
        
        # To, CC, BCC
        headers['to_addresses'] = self._parse_address_list(msg.get('To', ''))
        headers['cc_addresses'] = self._parse_address_list(msg.get('CC', ''))
        headers['bcc_addresses'] = self._parse_address_list(msg.get('BCC', ''))
        
        # Reply-To
        reply_to = msg.get('Reply-To')
        if reply_to:
            headers['reply_to'] = self._parse_address_list(reply_to)[0]
        
        # Subject
        headers['subject'] = msg.get('Subject')
        
        # Date
        date_str = msg.get('Date')
        if date_str:
            try:
                headers['sent_at'] = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                logger.warning(f"Failed to parse date: {date_str}")
        
        headers['received_at'] = datetime.utcnow()
        
        # Threading
        headers['in_reply_to'] = msg.get('In-Reply-To')
        references_str = msg.get('References', '')
        if references_str:
            headers['references'] = references_str.split()
        
        return headers

    def _parse_address_list(self, address_str: str) -> List[str]:
        """Parse comma-separated email addresses."""
        if not address_str:
            return []
        
        addresses = []
        for addr in address_str.split(','):
            addr = addr.strip()
            if '<' in addr:
                addr = addr.split('<')[1].strip('>')
            addresses.append(addr)
        
        return addresses

    def _parse_body(self, msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text/plain and text/html body parts.
        
        Returns:
            (body_text, body_html)
        """
        body_text = None
        body_html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                
                if content_type == 'text/plain' and not body_text:
                    try:
                        body_text = part.get_content()
                    except Exception as e:
                        logger.error(f"Failed to decode text/plain: {e}")
                
                elif content_type == 'text/html' and not body_html:
                    try:
                        body_html = part.get_content()
                    except Exception as e:
                        logger.error(f"Failed to decode text/html: {e}")
        else:
            # Non-multipart email
            content_type = msg.get_content_type()
            try:
                if content_type == 'text/plain':
                    body_text = msg.get_content()
                elif content_type == 'text/html':
                    body_html = msg.get_content()
            except Exception as e:
                logger.error(f"Failed to decode body: {e}")
        
        return body_text, body_html

    def _parse_attachments(self, msg: EmailMessage) -> List[dict]:
        """Extract attachments from email."""
        attachments = []
        
        if not msg.is_multipart():
            return attachments
        
        for part in msg.walk():
            # Skip text parts
            if part.get_content_type() in ('text/plain', 'text/html'):
                continue
            
            # Check if attachment
            if part.get_content_disposition() in ('attachment', 'inline'):
                filename = part.get_filename()
                if not filename:
                    # Generate filename for inline images
                    ext = part.get_content_subtype()
                    filename = f"attachment_{uuid4()}.{ext}"
                
                try:
                    content = part.get_content()
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    
                    att_data = {
                        'filename': filename,
                        'content': content,
                        'content_type': part.get_content_type(),
                        'is_inline': part.get_content_disposition() == 'inline',
                        'content_id': part.get('Content-ID', '').strip('<>'),
                    }
                    attachments.append(att_data)
                    
                except Exception as e:
                    logger.error(f"Failed to extract attachment {filename}: {e}")
        
        return attachments

    async def _upload_to_s3(
        self,
        content: bytes,
        filename: str,
        content_type: str
    ) -> str:
        """
        Upload attachment to S3.
        
        Returns:
            S3 key (path)
        """
        # Generate S3 key: emails/{year}/{month}/{day}/{uuid}/{filename}
        now = datetime.utcnow()
        s3_key = (
            f"emails/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{uuid4()}/{filename}"
        )
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
            )
            logger.info(f"Uploaded {filename} to s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}", exc_info=True)
            raise
```

---

## 💾 DATABASESERVICE

### File: `app/services/database.py`

```python
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.email_models import (
    EmailCreate,
    EmailDB,
    EmailWithAttachments,
    AttachmentCreate,
    AttachmentDB,
    ClassificationResult,
    ERPActionStatus,
)
from app.db.models import (
    Email,
    Attachment,
    Contact,
    Thread,
    ClassificationHistory,
    ERPAction,
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Async database service для работы с PostgreSQL через SQLAlchemy 2.0.
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_email(
        self,
        email_data: EmailCreate,
        attachments: Optional[List[AttachmentCreate]] = None
    ) -> EmailWithAttachments:
        """
        Create new email record с attachments.
        
        Args:
            email_data: Email data
            attachments: List of attachments (optional)
            
        Returns:
            Created EmailWithAttachments object
        """
        try:
            # Create email record
            email = Email(**email_data.dict())
            email.has_attachments = bool(attachments)
            email.attachment_count = len(attachments) if attachments else 0
            
            self.session.add(email)
            await self.session.flush()  # Get email.id
            
            # Create attachments
            att_objects = []
            if attachments:
                for att_data in attachments:
                    att = Attachment(**att_data.dict(), email_id=email.id)
                    self.session.add(att)
                    att_objects.append(att)
            
            # Update contact statistics
            await self._update_contact(email_data.from_address, email_data.from_name)
            
            # Commit transaction
            await self.session.commit()
            await self.session.refresh(email)
            
            logger.info(f"Created email {email.id} with {len(att_objects)} attachments")
            
            return EmailWithAttachments(
                **EmailDB.from_orm(email).dict(),
                attachments=[AttachmentDB.from_orm(a) for a in att_objects]
            )
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create email: {e}", exc_info=True)
            raise

    async def get_email(self, email_id: UUID) -> Optional[EmailWithAttachments]:
        """Get email by ID with attachments."""
        stmt = (
            select(Email)
            .options(selectinload(Email.attachments))
            .where(Email.id == email_id)
        )
        result = await self.session.execute(stmt)
        email = result.scalar_one_or_none()
        
        if not email:
            return None
        
        return EmailWithAttachments(
            **EmailDB.from_orm(email).dict(),
            attachments=[AttachmentDB.from_orm(a) for a in email.attachments]
        )

    async def update_classification(
        self,
        email_id: UUID,
        classification: ClassificationResult
    ) -> EmailDB:
        """
        Update email classification.
        
        Also creates classification_history record.
        """
        try:
            # Get email
            stmt = select(Email).where(Email.id == email_id)
            result = await self.session.execute(stmt)
            email = result.scalar_one_or_none()
            
            if not email:
                raise ValueError(f"Email {email_id} not found")
            
            # Update email
            email.intent = classification.intent
            email.sentiment = classification.sentiment
            email.priority = classification.priority
            email.confidence_score = classification.confidence_score
            email.classified_at = datetime.utcnow()
            
            # Create history record
            history = ClassificationHistory(
                email_id=email_id,
                intent=classification.intent,
                sentiment=classification.sentiment,
                priority=classification.priority,
                confidence_score=classification.confidence_score,
                llm_model="llama-3.1-8b",  # TODO: Make configurable
                llm_response=classification.reasoning,
            )
            self.session.add(history)
            
            await self.session.commit()
            await self.session.refresh(email)
            
            logger.info(f"Updated classification for email {email_id}: {classification.intent}")
            
            return EmailDB.from_orm(email)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update classification: {e}", exc_info=True)
            raise

    async def get_emails_pending_classification(
        self,
        limit: int = 100
    ) -> List[EmailDB]:
        """Get emails waiting for classification."""
        stmt = (
            select(Email)
            .where(
                and_(
                    Email.intent.is_(None),
                    Email.classified_at.is_(None)
                )
            )
            .order_by(Email.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        emails = result.scalars().all()
        
        return [EmailDB.from_orm(e) for e in emails]

    async def get_emails_last_24h(self) -> int:
        """Count emails received in last 24 hours."""
        since = datetime.utcnow() - timedelta(hours=24)
        stmt = select(func.count(Email.id)).where(Email.received_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_total_emails(self) -> int:
        """Count total emails."""
        stmt = select(func.count(Email.id))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def _update_contact(self, email: str, name: Optional[str] = None):
        """Update or create contact record."""
        try:
            stmt = select(Contact).where(Contact.email == email)
            result = await self.session.execute(stmt)
            contact = result.scalar_one_or_none()
            
            if contact:
                # Update existing
                contact.emails_received_count += 1
                contact.last_email_at = datetime.utcnow()
                if name and not contact.name:
                    contact.name = name
            else:
                # Create new
                contact = Contact(
                    email=email,
                    name=name,
                    emails_received_count=1,
                    last_email_at=datetime.utcnow()
                )
                self.session.add(contact)
            
            await self.session.flush()
            
        except Exception as e:
            logger.error(f"Failed to update contact {email}: {e}")

    async def create_erp_action(
        self,
        email_id: UUID,
        action_type: str,
        entity_type: str,
        entity_id: str,
        request_payload: dict
    ) -> UUID:
        """Create ERP action record."""
        try:
            action = ERPAction(
                email_id=email_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                request_payload=request_payload,
                status="pending"
            )
            self.session.add(action)
            await self.session.commit()
            await self.session.refresh(action)
            
            logger.info(f"Created ERP action {action.id} for email {email_id}")
            
            return action.id
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create ERP action: {e}", exc_info=True)
            raise

    async def update_erp_action(
        self,
        action_id: UUID,
        status: ERPActionStatus,
        response_payload: Optional[dict] = None,
        error_message: Optional[str] = None
    ):
        """Update ERP action status."""
        try:
            stmt = select(ERPAction).where(ERPAction.id == action_id)
            result = await self.session.execute(stmt)
            action = result.scalar_one_or_none()
            
            if not action:
                raise ValueError(f"ERP action {action_id} not found")
            
            action.status = status
            if response_payload:
                action.response_payload = response_payload
            if error_message:
                action.error_message = error_message
            if status in ("success", "failed"):
                action.completed_at = datetime.utcnow()
            
            await self.session.commit()
            
            logger.info(f"Updated ERP action {action_id} status: {status}")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update ERP action: {e}", exc_info=True)
            raise
```

---

*Файл продолжение следует в следующей части из-за ограничения размера. Вторая часть будет содержать:*
- FastAPI Application
- Unit Tests
- Integration Tests
- Docker Deployment
- Monitoring & Metrics

**Общий размер файла:** ~1500 строк
