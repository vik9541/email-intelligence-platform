# 🚀 БЫСТРЫЙ СТАРТ: 8 Команд для GitHub Copilot

> **Для:** VS Code + GitHub Copilot  
> **Время выполнения:** 2-3 часа  
> **Результат:** 1,700+ строк production-ready кода  
> **Последнее обновление:** 15 декабря 2025 г.

---

## 📋 КАК ИСПОЛЬЗОВАТЬ

### Шаг 1: Откройте Copilot Chat
- Windows/Linux: `Ctrl+Alt+I`
- macOS: `Cmd+Opt+I`
- Или: `Ctrl+Shift+P` → "GitHub Copilot: Open Copilot Chat"

### Шаг 2: Скопируйте команду
- Выберите одну из 8 команд ниже
- Скопируйте весь текст (включая примеры и требования)

### Шаг 3: Вставьте в Copilot Chat
- Вставьте: `Ctrl+V` (или `Cmd+V`)
- Нажмите Enter

### Шаг 4: Примените сгенерированный код
- Нажмите кнопку "Apply in Editor"
- Или скопируйте код вручную в созданный файл

### Шаг 5: Повторите для остальных команд
- Выполните все 8 команд по порядку

---

## ✅ ЧЕКЛИСТ

- [ ] КОМАНДА 1: PostgreSQL Schema (15 мин, ~350 строк SQL)
- [ ] КОМАНДА 2: Pydantic Models (15 мин, ~200 строк Python)
- [ ] КОМАНДА 3: Email Parser (30 мин, ~250 строк Python)
- [ ] КОМАНДА 4: Database Service (20 мин, ~200 строк Python)
- [ ] КОМАНДА 5: FastAPI Application (30 мин, ~200 строк Python)
- [ ] КОМАНДА 6: Unit + Integration Tests (30 мин, ~200 строк Python)
- [ ] КОМАНДА 7: Docker Files (20 мин, ~190 строк YAML/Dockerfile)
- [ ] КОМАНДА 8: Requirements + Documentation (10 мин, ~145 строк)

**ИТОГО:** ~2-3 часа, 1,735 строк кода

---

# КОМАНДА 1: Создать PostgreSQL Schema

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай файл `migrations/001_init_schema.sql` с PostgreSQL schema для Email Intelligence Platform.

**Требования:**

1. **Таблица `emails`** (основная таблица писем):
   - `id` UUID PRIMARY KEY
   - `message_id` VARCHAR(255) UNIQUE (IMAP Message-ID)
   - `imap_uid` BIGINT, `imap_folder` VARCHAR(100)
   - Headers: `from_address`, `from_name`, `to_addresses TEXT[]`, `cc_addresses TEXT[]`, `bcc_addresses TEXT[]`, `reply_to`, `subject`, `body_text`, `body_html`
   - Threading: `thread_id UUID REFERENCES threads`, `in_reply_to`, `references TEXT[]`
   - Classification: `intent` (invoice/order/complaint/inquiry/newsletter/spam/other), `sentiment` (positive/neutral/negative), `priority` (low/normal/high/urgent), `confidence_score NUMERIC(3,2)`
   - ERP: `erp_entity_type`, `erp_entity_id`, `erp_action_status` (pending/processing/completed/failed), `erp_action_result JSONB`
   - Metadata: `size_bytes`, `has_attachments BOOLEAN`, `attachment_count`, `flags TEXT[]`
   - Timestamps: `received_at`, `sent_at`, `parsed_at`, `classified_at`, `created_at`, `updated_at`

2. **Таблица `attachments`**:
   - `id` UUID PRIMARY KEY
   - `email_id UUID REFERENCES emails ON DELETE CASCADE`
   - File info: `filename`, `content_type`, `size_bytes`, `md5_hash`
   - S3 storage: `s3_bucket`, `s3_key`, `s3_url`
   - Metadata: `is_inline BOOLEAN`, `content_id` (for inline images)
   - Virus scan: `virus_scan_status` (pending/clean/infected/failed), `virus_scan_result JSONB`
   - Timestamps: `created_at`, `updated_at`

3. **Таблица `contacts`**:
   - `id` UUID PRIMARY KEY
   - `email VARCHAR(255) UNIQUE`, `name`
   - Statistics: `emails_sent_count`, `emails_received_count`, `last_email_at`
   - Classification: `is_customer`, `is_supplier`, `is_internal` (все BOOLEAN)
   - ERP: `erp_customer_id`, `erp_supplier_id`
   - Timestamps: `created_at`, `updated_at`

4. **Таблица `threads`**:
   - `id` UUID PRIMARY KEY
   - `subject TEXT`, `participant_emails TEXT[]`
   - Statistics: `email_count`, `last_email_at`
   - `intent`, `status` (active/resolved/archived)
   - Timestamps: `created_at`, `updated_at`

5. **Таблица `classification_history`** (audit trail для LLM):
   - `id` UUID PRIMARY KEY
   - `email_id UUID REFERENCES emails ON DELETE CASCADE`
   - Result: `intent`, `sentiment`, `priority`, `confidence_score`
   - LLM details: `llm_model`, `llm_prompt TEXT`, `llm_response TEXT`, `llm_latency_ms`
   - `classified_at TIMESTAMP WITH TIME ZONE`

6. **Таблица `erp_actions`**:
   - `id` UUID PRIMARY KEY
   - `email_id UUID REFERENCES emails ON DELETE CASCADE`
   - Action: `action_type` (create_order/update_invoice/etc.), `entity_type`, `entity_id`
   - Request/Response: `request_payload JSONB`, `response_payload JSONB`
   - Status: `status` (pending/success/failed/retrying), `error_message`, `retry_count`
   - Timestamps: `executed_at`, `completed_at`

7. **Таблица `processing_queue`**:
   - `id` UUID PRIMARY KEY
   - `email_id UUID REFERENCES emails ON DELETE CASCADE`
   - Queue: `queue_name` (parsing/classification/erp_action), `priority INTEGER` (1-10)
   - Processing: `status` (pending/processing/completed/failed), `attempts`, `max_attempts`, `last_error`
   - Timestamps: `created_at`, `scheduled_at`, `started_at`, `completed_at`

8. **Таблица `api_metrics`**:
   - `id` UUID PRIMARY KEY
   - Request: `endpoint`, `method`, `status_code`, `latency_ms`
   - User: `client_ip`, `user_agent`
   - `created_at TIMESTAMP WITH TIME ZONE`

**Индексы (минимум 15):**
- `idx_emails_message_id ON emails(message_id)`
- `idx_emails_from_address ON emails(from_address)`
- `idx_emails_thread_id ON emails(thread_id)`
- `idx_emails_received_at ON emails(received_at DESC)`
- `idx_emails_intent ON emails(intent) WHERE intent IS NOT NULL`
- `idx_emails_erp_status ON emails(erp_action_status)`
- `idx_emails_has_attachments ON emails(has_attachments) WHERE has_attachments = TRUE`
- `idx_emails_subject_fts ON emails USING gin(to_tsvector('russian', subject))`
- `idx_emails_body_fts ON emails USING gin(to_tsvector('russian', body_text))`
- `idx_attachments_email_id ON attachments(email_id)`
- `idx_attachments_md5_hash ON attachments(md5_hash)`
- `idx_contacts_email ON contacts(email)`
- `idx_threads_last_email_at ON threads(last_email_at DESC)`
- `idx_queue_status_priority ON processing_queue(status, priority DESC, scheduled_at ASC)`
- `idx_metrics_endpoint ON api_metrics(endpoint)`

**Triggers:**
- `trg_emails_updated_at` - Auto-update `updated_at` на UPDATE для `emails`
- `trg_attachments_updated_at` - Auto-update для `attachments`
- `trg_contacts_updated_at` - Auto-update для `contacts`
- `trg_threads_updated_at` - Auto-update для `threads`

**Views (3 штуки):**
1. `email_stats_by_sender` - GROUP BY from_address с COUNT, AVG(size_bytes), MAX(received_at), ARRAY_AGG(intent)
2. `email_volume_daily` - GROUP BY DATE(received_at) с COUNT по каждому intent
3. `erp_action_stats` - GROUP BY action_type с success_rate_pct и avg_duration_sec

**Function:**
- `update_updated_at_column()` - для trigger updated_at (RETURNS TRIGGER, NEW.updated_at = NOW())
- `cleanup_old_queue_items()` - DELETE FROM processing_queue WHERE status IN ('completed', 'failed') AND completed_at < NOW() - INTERVAL '7 days'

**ВАЖНО:**
- Используй PostgreSQL 15+ синтаксис
- Все PRIMARY KEY должны быть UUID с DEFAULT gen_random_uuid()
- Все TIMESTAMP должны быть WITH TIME ZONE
- Все TEXT[] должны иметь DEFAULT '{}'
- Добавь комментарии к сложным индексам

**Ожидаемый размер:** ~350-400 строк SQL

Сгенерируй полный SQL файл с:
1. CREATE TABLE для всех 8 таблиц
2. CREATE INDEX для всех индексов
3. CREATE TRIGGER для всех триггеров
4. CREATE VIEW для всех views
5. CREATE FUNCTION для всех функций
```

---

**Проверка:**
После генерации убедитесь, что файл `migrations/001_init_schema.sql` содержит:
- ✅ 8 таблиц (emails, attachments, contacts, threads, classification_history, erp_actions, processing_queue, api_metrics)
- ✅ 15+ индексов
- ✅ 4 триггера
- ✅ 3 views
- ✅ 2 функции

---

# КОМАНДА 2: Создать Pydantic Models

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай файл `app/models/email_models.py` с Pydantic models для Email Intelligence Platform.

**Требования:**

1. **Enums (6 штук):**
   - `EmailIntent(str, Enum)`: INVOICE, ORDER, COMPLAINT, INQUIRY, NEWSLETTER, SPAM, OTHER
   - `EmailSentiment(str, Enum)`: POSITIVE, NEUTRAL, NEGATIVE
   - `EmailPriority(str, Enum)`: LOW, NORMAL, HIGH, URGENT
   - `ERPActionStatus(str, Enum)`: PENDING, PROCESSING, COMPLETED, FAILED
   - `VirusScanStatus(str, Enum)`: PENDING, CLEAN, INFECTED, FAILED
   - `ThreadStatus(str, Enum)`: ACTIVE, RESOLVED, ARCHIVED

2. **Base Models:**

   **AttachmentBase:**
   - `filename: str` (Field max_length=255)
   - `content_type: Optional[str]` (max_length=100)
   - `size_bytes: int` (Field ge=0)
   - `md5_hash: Optional[str]` (max_length=32)
   - `is_inline: bool = False`
   - `content_id: Optional[str]`

   **AttachmentCreate (extends AttachmentBase):**
   - `email_id: UUID`
   - `s3_bucket: Optional[str]`
   - `s3_key: Optional[str]`

   **AttachmentDB (extends AttachmentBase):**
   - `id: UUID`
   - `email_id: UUID`
   - `s3_bucket: Optional[str]`
   - `s3_key: Optional[str]`
   - `s3_url: Optional[str]`
   - `virus_scan_status: VirusScanStatus`
   - `virus_scan_result: Optional[dict]`
   - `created_at: datetime`
   - `updated_at: datetime`
   - `Config: from_attributes = True`

   **EmailBase:**
   - `message_id: str` (max_length=255)
   - `from_address: EmailStr`
   - `from_name: Optional[str]` (max_length=255)
   - `to_addresses: List[EmailStr]` (min_items=1)
   - `cc_addresses: Optional[List[EmailStr]] = []`
   - `bcc_addresses: Optional[List[EmailStr]] = []`
   - `reply_to: Optional[EmailStr]`
   - `subject: Optional[str]`
   - `body_text: Optional[str]`
   - `body_html: Optional[str]`
   - `received_at: datetime`
   - `sent_at: Optional[datetime]`
   - **Validator** `validate_email_lists` для to_addresses/cc_addresses/bcc_addresses - удаляет дубликаты через set()

   **EmailCreate (extends EmailBase):**
   - `imap_uid: Optional[int]`
   - `imap_folder: str = "INBOX"`
   - `in_reply_to: Optional[str]`
   - `references: Optional[List[str]] = []`
   - `size_bytes: Optional[int]`
   - `flags: Optional[List[str]] = []`

   **EmailDB (extends EmailBase):**
   - `id: UUID`
   - `imap_uid: Optional[int]`
   - `imap_folder: str`
   - `thread_id: Optional[UUID]`
   - `in_reply_to: Optional[str]`
   - `references: Optional[List[str]]`
   - `intent: Optional[EmailIntent]`
   - `sentiment: Optional[EmailSentiment]`
   - `priority: EmailPriority`
   - `confidence_score: Optional[float]` (ge=0.0, le=1.0)
   - `erp_entity_type: Optional[str]`
   - `erp_entity_id: Optional[str]`
   - `erp_action_status: ERPActionStatus`
   - `erp_action_result: Optional[dict]`
   - `size_bytes: Optional[int]`
   - `has_attachments: bool`
   - `attachment_count: int`
   - `flags: Optional[List[str]]`
   - `parsed_at: datetime`
   - `classified_at: Optional[datetime]`
   - `created_at: datetime`
   - `updated_at: datetime`
   - `Config: from_attributes = True`

   **EmailWithAttachments (extends EmailDB):**
   - `attachments: List[AttachmentDB] = []`

3. **Classification Models:**

   **ClassificationRequest:**
   - `email_id: UUID`
   - `subject: str`
   - `body_text: str`
   - `from_address: EmailStr`

   **ClassificationResult:**
   - `intent: EmailIntent`
   - `sentiment: EmailSentiment`
   - `priority: EmailPriority`
   - `confidence_score: float` (ge=0.0, le=1.0)
   - `reasoning: Optional[str]` (explanation from LLM)

4. **API Request/Response Models:**

   **ParseEmailRequest:**
   - `raw_email: bytes` (description="Raw email in RFC822 format")
   - `imap_uid: Optional[int]`
   - `imap_folder: str = "INBOX"`

   **ParseEmailResponse:**
   - `email: EmailWithAttachments`
   - `processing_time_ms: int`

   **HealthCheckResponse:**
   - `status: str`
   - `database: str`
   - `redis: Optional[str]`
   - `kafka: Optional[str]`
   - `timestamp: datetime`

   **MetricsResponse:**
   - `total_emails: int`
   - `emails_last_24h: int`
   - `emails_pending_classification: int`
   - `emails_pending_erp_action: int`
   - `avg_classification_time_ms: float`
   - `avg_parse_time_ms: float`

**Imports:**
```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum
```

**ВАЖНО:**
- Все модели должны иметь docstrings
- Используй type hints везде
- Validators должны возвращать обработанное значение
- Config class должен быть внутри каждой DB модели

**Ожидаемый размер:** ~200-250 строк Python

Сгенерируй полный Python файл с:
1. Всеми Enums (6 штук)
2. Всеми Base/Create/DB моделями для Attachment и Email
3. Classification моделями
4. API Request/Response моделями
5. Validators где необходимо
```

---

**Проверка:**
После генерации убедитесь, что файл `app/models/email_models.py` содержит:
- ✅ 6 Enums
- ✅ 10+ Pydantic models
- ✅ Validators для email lists
- ✅ Type hints везде

---

# КОМАНДА 3: Создать Email Parser Service

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай файл `app/services/email_parser.py` с асинхронным email parser для Email Intelligence Platform.

**Требования:**

1. **Класс `EmailParserService`:**
   - `__init__(self, s3_bucket: str, s3_client: Optional[boto3.client] = None)`
   - Создаёт S3 client если не передан

2. **Главный метод `async def parse_email(self, raw_email: bytes) -> EmailWithAttachments`:**
   - Парсит raw email через `email.message_from_bytes(raw_email, policy=policy.default)`
   - Извлекает headers через `_parse_headers(msg)`
   - Извлекает body через `_parse_body(msg)` → returns (body_text, body_html)
   - Извлекает attachments через `_parse_attachments(msg)` → returns List[dict]
   - Загружает attachments в S3 через `_upload_to_s3()`
   - Возвращает `EmailWithAttachments` object
   - Логирует время парсинга в миллисекундах
   - **Exception handling:** При ошибке логирует `exc_info=True` и re-raise

3. **Метод `_parse_headers(self, msg: EmailMessage) -> dict`:**
   - Message-ID: `msg.get('Message-ID', str(uuid4()))`
   - From: парсит "Name <email@example.com>" → `from_name` и `from_address`
   - To, CC, BCC: через `_parse_address_list()`
   - Reply-To: опционально
   - Subject: `msg.get('Subject')`
   - Date: через `email.utils.parsedate_to_datetime()` → `sent_at`
   - received_at: `datetime.utcnow()`
   - Threading: `In-Reply-To`, `References` (split by space)
   - Returns dict с всеми headers

4. **Метод `_parse_address_list(self, address_str: str) -> List[str]`:**
   - Split by comma
   - Если "<>" present → extract email between <>
   - Returns list of email addresses

5. **Метод `_parse_body(self, msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]`:**
   - Если multipart → walk through parts
   - Ищет `content_type == 'text/plain'` → `body_text`
   - Ищет `content_type == 'text/html'` → `body_html`
   - Использует `part.get_content()` для декодирования
   - **Exception handling:** try/except для UnicodeDecodeError
   - Returns (body_text, body_html)

6. **Метод `_parse_attachments(self, msg: EmailMessage) -> List[dict]`:**
   - Skip если non-multipart
   - Для каждого part:
     - Skip если text/plain или text/html
     - Проверяет `Content-Disposition` in ('attachment', 'inline')
     - Извлекает filename или генерирует `attachment_{uuid}.{ext}`
     - Получает content через `part.get_content()`
     - Если content is str → encode to bytes
     - Собирает dict: `{'filename', 'content', 'content_type', 'is_inline', 'content_id'}`
   - **Exception handling:** try/except per attachment
   - Returns List[dict]

7. **Метод `async def _upload_to_s3(self, content: bytes, filename: str, content_type: str) -> str`:**
   - Генерирует S3 key: `emails/{year}/{month}/{day}/{uuid}/{filename}`
   - Использует `datetime.utcnow()` для path
   - Вызывает `s3_client.put_object(Bucket=..., Key=..., Body=..., ContentType=...)`
   - **Exception handling:** ClientError → logger.error + re-raise
   - Returns s3_key

**Imports:**
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
```

**Logging:**
- `logger = logging.getLogger(__name__)`
- Используй `logger.info()` для успешных операций
- Используй `logger.error(..., exc_info=True)` для ошибок
- Логирование:
  - После parse_email: `f"Parsed email {message_id} in {parse_time_ms}ms ({len(attachments)} attachments)"`
  - После upload_to_s3: `f"Uploaded {filename} to s3://{bucket}/{key}"`
  - При ошибке: `f"Failed to parse email: {e}"`

**ВАЖНО:**
- Все методы должны иметь docstrings в Google Style
- Type hints везде
- Exception handling в каждом методе
- MD5 hash для attachments: `hashlib.md5(content).hexdigest()`

**Пример входных данных:**
```python
raw_email = b"""From: John Doe <john@example.com>
To: jane@example.com
Subject: Test Email
Content-Type: text/plain; charset=utf-8

Hello World
"""
```

**Ожидаемый результат:**
```python
EmailWithAttachments(
    message_id="...",
    from_address="john@example.com",
    from_name="John Doe",
    to_addresses=["jane@example.com"],
    subject="Test Email",
    body_text="Hello World",
    attachments=[],
    ...
)
```

**Ожидаемый размер:** ~250-300 строк Python

Сгенерируй полный Python файл с:
1. Класс EmailParserService
2. Все 7 методов с docstrings
3. Exception handling
4. Logging
5. Type hints
```

---

**Проверка:**
После генерации убедитесь, что файл `app/services/email_parser.py` содержит:
- ✅ Класс EmailParserService
- ✅ 7 методов (parse_email, _parse_headers, _parse_address_list, _parse_body, _parse_attachments, _upload_to_s3, __init__)
- ✅ Exception handling в каждом методе
- ✅ Logging

---

# КОМАНДА 4: Создать Database Service

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай файл `app/services/database.py` с async database service для Email Intelligence Platform используя SQLAlchemy 2.0.

**Требования:**

1. **Класс `DatabaseService`:**
   - `__init__(self, session: AsyncSession)`
   - Сохраняет session как `self.session`

2. **Метод `async def create_email(self, email_data: EmailCreate, attachments: Optional[List[AttachmentCreate]] = None) -> EmailWithAttachments`:**
   - Создаёт Email record: `email = Email(**email_data.dict())`
   - Устанавливает `email.has_attachments = bool(attachments)`
   - Устанавливает `email.attachment_count = len(attachments) if attachments else 0`
   - Добавляет в session: `self.session.add(email)`
   - Делает flush для получения email.id: `await self.session.flush()`
   - Создаёт Attachment records в цикле, устанавливая `email_id=email.id`
   - Вызывает `await self._update_contact(email_data.from_address, email_data.from_name)`
   - Делает commit: `await self.session.commit()`
   - Делает refresh: `await self.session.refresh(email)`
   - Логирует: `f"Created email {email.id} with {len(attachments)} attachments"`
   - **Exception handling:** При ошибке → `await self.session.rollback()` + logger.error + re-raise
   - Returns `EmailWithAttachments`

3. **Метод `async def get_email(self, email_id: UUID) -> Optional[EmailWithAttachments]`:**
   - Создаёт statement: `stmt = select(Email).options(selectinload(Email.attachments)).where(Email.id == email_id)`
   - Выполняет: `result = await self.session.execute(stmt)`
   - Получает: `email = result.scalar_one_or_none()`
   - Если None → return None
   - Конвертирует в EmailWithAttachments через `EmailDB.from_orm(email)`
   - Returns EmailWithAttachments

4. **Метод `async def update_classification(self, email_id: UUID, classification: ClassificationResult) -> EmailDB`:**
   - Получает email: `stmt = select(Email).where(Email.id == email_id)`
   - Если не найден → raise `ValueError(f"Email {email_id} not found")`
   - Обновляет поля:
     - `email.intent = classification.intent`
     - `email.sentiment = classification.sentiment`
     - `email.priority = classification.priority`
     - `email.confidence_score = classification.confidence_score`
     - `email.classified_at = datetime.utcnow()`
   - Создаёт ClassificationHistory record:
     - `history = ClassificationHistory(email_id=email_id, intent=..., llm_model="llama-3.1-8b", llm_response=classification.reasoning, ...)`
     - `self.session.add(history)`
   - Делает commit и refresh
   - Логирует: `f"Updated classification for email {email_id}: {classification.intent}"`
   - **Exception handling:** rollback при ошибке
   - Returns `EmailDB.from_orm(email)`

5. **Метод `async def get_emails_pending_classification(self, limit: int = 100) -> List[EmailDB]`:**
   - Statement: `select(Email).where(and_(Email.intent.is_(None), Email.classified_at.is_(None))).order_by(Email.received_at.desc()).limit(limit)`
   - Выполняет и возвращает список `EmailDB`

6. **Метод `async def get_emails_last_24h(self) -> int`:**
   - Считает emails где `received_at >= datetime.utcnow() - timedelta(hours=24)`
   - Использует `func.count(Email.id)`
   - Returns int

7. **Метод `async def get_total_emails(self) -> int`:**
   - Считает все emails: `func.count(Email.id)`
   - Returns int

8. **Метод `async def _update_contact(self, email: str, name: Optional[str] = None)`:**
   - Ищет Contact: `select(Contact).where(Contact.email == email)`
   - Если найден:
     - `contact.emails_received_count += 1`
     - `contact.last_email_at = datetime.utcnow()`
     - `if name and not contact.name: contact.name = name`
   - Если не найден → создаёт новый:
     - `contact = Contact(email=email, name=name, emails_received_count=1, last_email_at=datetime.utcnow())`
     - `self.session.add(contact)`
   - Делает flush (БЕЗ commit - вызывается внутри другой транзакции)
   - **Exception handling:** try/except → logger.error (не re-raise)

9. **Метод `async def create_erp_action(self, email_id: UUID, action_type: str, entity_type: str, entity_id: str, request_payload: dict) -> UUID`:**
   - Создаёт ERPAction: `action = ERPAction(..., status="pending")`
   - Добавляет, commit, refresh
   - Логирует: `f"Created ERP action {action.id} for email {email_id}"`
   - Returns `action.id`

10. **Метод `async def update_erp_action(self, action_id: UUID, status: ERPActionStatus, response_payload: Optional[dict] = None, error_message: Optional[str] = None)`:**
    - Находит ERPAction по ID
    - Обновляет `status`, `response_payload`, `error_message`
    - Если status in ("success", "failed") → `action.completed_at = datetime.utcnow()`
    - Commit
    - Логирует: `f"Updated ERP action {action_id} status: {status}"`

**Imports:**
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
```

**ВАЖНО:**
- Все методы async
- Используй SQLAlchemy 2.0 синтаксис (`select()` вместо `query()`)
- Все DB операции через async session
- Exception handling с rollback
- Type hints везде
- Docstrings для публичных методов

**Ожидаемый размер:** ~200-250 строк Python

Сгенерируй полный Python файл с:
1. Класс DatabaseService
2. Все 10+ методов
3. Exception handling
4. Logging
5. Type hints
```

---

**Проверка:**
После генерации убедитесь, что файл `app/services/database.py` содержит:
- ✅ Класс DatabaseService
- ✅ 10+ async методов
- ✅ SQLAlchemy 2.0 синтаксис
- ✅ Exception handling с rollback

---

# КОМАНДА 5: Создать FastAPI Application

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай файл `app/main.py` с FastAPI приложением для Email Intelligence Platform.

**Требования:**

1. **FastAPI App Setup:**
   - `app = FastAPI(title="Email Intelligence Platform", version="1.0.0")`
   - CORS middleware: `app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`
   - Prometheus middleware для метрик

2. **Dependency Injection:**
   - `async def get_db_session() -> AsyncIterator[AsyncSession]`:
     - Создаёт async session
     - `async with async_session_maker() as session: yield session`
   - `async def get_database_service(session: AsyncSession = Depends(get_db_session)) -> DatabaseService`:
     - Returns `DatabaseService(session)`
   - `async def get_email_parser() -> EmailParserService`:
     - Returns `EmailParserService(s3_bucket=settings.S3_BUCKET)`

3. **Endpoint: `GET /health`:**
   - Returns `HealthCheckResponse`
   - Проверяет database connection:
     - `await session.execute(select(1))`
     - Если success → `database="connected"`
     - Если fail → `database="disconnected"`
   - Returns:
     ```python
     {
         "status": "healthy",
         "database": "connected",
         "timestamp": datetime.utcnow()
     }
     ```

4. **Endpoint: `GET /ready`:**
   - Аналогично `/health` но возвращает 503 если database disconnected
   - Use case: Kubernetes readiness probe

5. **Endpoint: `POST /parse`:**
   - Request body: `ParseEmailRequest`
   - Dependency: `EmailParserService`, `DatabaseService`
   - Логика:
     1. Парсит email: `email = await parser.parse_email(request.raw_email)`
     2. Сохраняет в БД: `email_db = await db.create_email(email, email.attachments)`
     3. Добавляет в processing queue (опционально)
     4. Считает `processing_time_ms`
   - Returns `ParseEmailResponse(email=email_db, processing_time_ms=...)`
   - **Exception handling:** HTTPException 400 при ошибке парсинга

6. **Endpoint: `POST /classify`:**
   - Request body: `ClassificationRequest`
   - Dependency: `DatabaseService`, LLM client (например Ollama)
   - Логика:
     1. Получает email из БД
     2. Формирует prompt для LLM:
        ```
        Classify this email:
        From: {from_address}
        Subject: {subject}
        Body: {body_text}
        
        Return JSON: {"intent": "...", "sentiment": "...", "priority": "...", "confidence": 0.0-1.0, "reasoning": "..."}
        ```
     3. Вызывает LLM
     4. Парсит JSON response
     5. Сохраняет classification: `await db.update_classification(email_id, result)`
   - Returns `ClassificationResult`
   - **Exception handling:** HTTPException 500 при ошибке LLM

7. **Endpoint: `GET /metrics`:**
   - Dependency: `DatabaseService`
   - Логика:
     1. Получает статистику:
        - `total_emails = await db.get_total_emails()`
        - `emails_last_24h = await db.get_emails_last_24h()`
        - `emails_pending_classification = len(await db.get_emails_pending_classification())`
     2. Считает avg times из api_metrics таблицы
   - Returns `MetricsResponse`

8. **Background Task: Process Pending Classifications:**
   - Функция `async def process_pending_classifications_task()`:
     - Бесконечный цикл `while True`:
       - Получает pending emails
       - Для каждого вызывает `/classify` endpoint
       - `await asyncio.sleep(60)` между итерациями
   - Запускается при startup: `@app.on_event("startup")`

**Imports:**
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from typing import AsyncIterator
import asyncio
import logging
from datetime import datetime

from app.models.email_models import (
    ParseEmailRequest,
    ParseEmailResponse,
    ClassificationRequest,
    ClassificationResult,
    HealthCheckResponse,
    MetricsResponse,
)
from app.services.email_parser import EmailParserService
from app.services.database import DatabaseService
```

**Settings (через pydantic-settings):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://email_user:email_pass@localhost:5432/email_db"
    S3_BUCKET: str = "email-attachments"
    OLLAMA_URL: str = "http://localhost:11434"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Logging setup:**
```python
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
```

**SQLAlchemy engine:**
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
```

**ВАЖНО:**
- Все endpoints async
- Exception handling с HTTPException
- Logging для всех операций
- Type hints везде
- Docstrings для endpoints

**Ожидаемый размер:** ~200-250 строк Python

Сгенерируй полный Python файл с:
1. FastAPI app setup
2. Dependency injection
3. 6 endpoints (/health, /ready, /parse, /classify, /metrics)
4. Background task для classification
5. Settings через pydantic-settings
6. SQLAlchemy async engine
```

---

**Проверка:**
После генерации убедитесь, что файл `app/main.py` содержит:
- ✅ FastAPI app с CORS
- ✅ 6 endpoints
- ✅ Dependency injection
- ✅ Background task

---

# КОМАНДА 6: Создать Unit + Integration Tests

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай 2 файла с тестами для Email Intelligence Platform:

**ФАЙЛ 1: `tests/test_email_parser.py`** (Unit tests для EmailParserService)

**Требования:**

1. **Fixture `email_parser`:**
   - Создаёт EmailParserService с mock S3 client
   - Использует `pytest.fixture`

2. **Fixture `sample_raw_email`:**
   - Returns bytes с простым email:
     ```
     From: john@example.com
     To: jane@example.com
     Subject: Test
     Content-Type: text/plain
     
     Hello
     ```

3. **Test `test_parse_simple_email(email_parser, sample_raw_email)`:**
   - Парсит sample_raw_email
   - Assert: `result.from_address == "john@example.com"`
   - Assert: `result.to_addresses == ["jane@example.com"]`
   - Assert: `result.subject == "Test"`
   - Assert: `result.body_text == "Hello"`

4. **Test `test_parse_email_with_attachment(email_parser)`:**
   - Создаёт multipart email с 1 PDF attachment
   - Парсит
   - Assert: `result.has_attachments == True`
   - Assert: `len(result.attachments) == 1`
   - Assert: `result.attachments[0].filename == "test.pdf"`

5. **Test `test_parse_email_with_inline_image(email_parser)`:**
   - Создаёт multipart email с inline image (Content-ID: <img1>)
   - Парсит
   - Assert: `result.attachments[0].is_inline == True`
   - Assert: `result.attachments[0].content_id == "img1"`

6. **Test `test_parse_invalid_email(email_parser)`:**
   - Пытается парсить невалидный bytes
   - Assert: raises Exception

**ФАЙЛ 2: `tests/test_integration.py`** (Integration tests)

**Требования:**

1. **Fixture `test_db_session`:**
   - Создаёт временную PostgreSQL БД (через testcontainers или sqlite)
   - Применяет миграции
   - Возвращает async session
   - После теста удаляет БД

2. **Fixture `database_service(test_db_session)`:**
   - Returns `DatabaseService(test_db_session)`

3. **Test `test_create_and_retrieve_email(database_service)`:**
   - Создаёт email через `database_service.create_email()`
   - Получает через `database_service.get_email(email_id)`
   - Assert: email retrieved successfully
   - Assert: все поля совпадают

4. **Test `test_classification_workflow(database_service)`:**
   - Создаёт email
   - Обновляет classification: `database_service.update_classification()`
   - Проверяет что:
     - `email.intent` обновился
     - `email.classified_at` не None
     - Создана запись в `classification_history`

5. **Test `test_contact_auto_update(database_service)`:**
   - Создаёт 2 emails от одного from_address
   - Проверяет что Contact record:
     - `emails_received_count == 2`
     - `last_email_at` обновился

**ФАЙЛ 3: `tests/conftest.py`** (Shared fixtures)

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        # TODO: Run CREATE TABLE statements
        pass
    
    yield engine
    await engine.dispose()

@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

**Imports для test_email_parser.py:**
```python
import pytest
from unittest.mock import Mock, patch
from app.services.email_parser import EmailParserService
```

**Imports для test_integration.py:**
```python
import pytest
from uuid import uuid4
from datetime import datetime
from app.services.database import DatabaseService
from app.models.email_models import EmailCreate, ClassificationResult, EmailIntent, EmailSentiment, EmailPriority
```

**ВАЖНО:**
- Все тесты async: `async def test_...()`
- Используй `@pytest.mark.asyncio` decorator
- Mock S3 client в unit tests
- Используй pytest fixtures
- Assert statements для всех проверок

**Ожидаемый размер:** ~200 строк Python (100 per file)

Сгенерируй 3 файла:
1. tests/test_email_parser.py (6 тестов)
2. tests/test_integration.py (5 тестов)
3. tests/conftest.py (shared fixtures)
```

---

**Проверка:**
После генерации убедитесь, что:
- ✅ tests/test_email_parser.py содержит 6 unit tests
- ✅ tests/test_integration.py содержит 5 integration tests
- ✅ tests/conftest.py содержит shared fixtures
- ✅ Все тесты async с `@pytest.mark.asyncio`

---

# КОМАНДА 7: Создать Docker Files

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай 2 файла для Docker deployment Email Intelligence Platform:

**ФАЙЛ 1: `Dockerfile`** (Multi-stage build для production)

**Требования:**

1. **Stage 1: Builder**
   - Base image: `python:3.11-slim`
   - Install build dependencies: `gcc postgresql-dev`
   - Install Python dependencies: `COPY requirements.txt` → `pip install --no-cache-dir -r requirements.txt`

2. **Stage 2: Runtime**
   - Base image: `python:3.11-slim`
   - Copy installed packages from builder: `COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages`
   - Copy app code: `COPY app/ /app/app/`
   - Working directory: `/app`
   - Expose port: `8000`
   - Health check: `HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1`
   - CMD: `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

**ФАЙЛ 2: `docker-compose.yml`** (6 сервисов)

**Требования:**

1. **Service: postgres**
   - Image: `postgres:15`
   - Environment:
     - `POSTGRES_DB=email_db`
     - `POSTGRES_USER=email_user`
     - `POSTGRES_PASSWORD=email_pass`
   - Ports: `5432:5432`
   - Volumes:
     - `postgres_data:/var/lib/postgresql/data`
     - `./migrations:/docker-entrypoint-initdb.d`
   - Healthcheck: `pg_isready -U email_user`

2. **Service: redis** (для caching)
   - Image: `redis:7-alpine`
   - Ports: `6379:6379`
   - Command: `redis-server --appendonly yes`
   - Volumes: `redis_data:/data`

3. **Service: kafka** (для message queue)
   - Image: `bitnami/kafka:latest`
   - Ports: `9092:9092`
   - Environment:
     - `KAFKA_BROKER_ID=1`
     - `KAFKA_LISTENERS=PLAINTEXT://:9092`
     - `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092`
     - `KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181`
   - Depends on: `zookeeper`

4. **Service: zookeeper**
   - Image: `bitnami/zookeeper:latest`
   - Ports: `2181:2181`
   - Environment: `ALLOW_ANONYMOUS_LOGIN=yes`

5. **Service: ollama** (LLM для classification)
   - Image: `ollama/ollama:latest`
   - Ports: `11434:11434`
   - Volumes: `ollama_data:/root/.ollama`
   - Command: `serve`

6. **Service: email-service** (наш FastAPI app)
   - Build: `context: .` `dockerfile: Dockerfile`
   - Ports: `8000:8000`
   - Environment:
     - `DATABASE_URL=postgresql+asyncpg://email_user:email_pass@postgres:5432/email_db`
     - `S3_BUCKET=email-attachments`
     - `OLLAMA_URL=http://ollama:11434`
     - `LOG_LEVEL=INFO`
   - Depends on: `postgres`, `redis`, `kafka`, `ollama`
   - Healthcheck: `curl -f http://localhost:8000/health`
   - Restart: `unless-stopped`

**Volumes:**
```yaml
volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

**Networks:**
```yaml
networks:
  default:
    name: email-platform
    driver: bridge
```

**ВАЖНО:**
- Dockerfile должен быть multi-stage для минимального размера image
- docker-compose.yml должен иметь healthchecks для всех сервисов
- Используй environment variables для конфигурации
- Volumes для persistent data (postgres, redis, ollama)

**Ожидаемый размер:** ~40 строк Dockerfile + ~150 строк docker-compose.yml

Сгенерируй 2 файла:
1. Dockerfile (multi-stage build)
2. docker-compose.yml (6 сервисов + volumes + networks)
```

---

**Проверка:**
После генерации убедитесь, что:
- ✅ Dockerfile использует multi-stage build
- ✅ docker-compose.yml содержит 6 сервисов
- ✅ Healthchecks настроены
- ✅ Volumes для persistent data

---

# КОМАНДА 8: Создать Requirements + Documentation

## 📄 Скопируйте эту команду в Copilot Chat:

```
Создай 2 финальных файла для Email Intelligence Platform:

**ФАЙЛ 1: `requirements.txt`**

**Требования:**

Добавь следующие зависимости с версиями:

**Web Framework:**
- `fastapi==0.109.0`
- `uvicorn[standard]==0.27.0`
- `pydantic==2.6.0`
- `pydantic-settings==2.1.0`

**Database:**
- `sqlalchemy==2.0.25`
- `asyncpg==0.29.0`
- `alembic==1.13.1`
- `psycopg2-binary==2.9.9`

**AWS / Storage:**
- `boto3==1.34.0`
- `botocore==1.34.0`

**Email Parsing:**
- (используем стандартную библиотеку `email`)

**Testing:**
- `pytest==8.0.0`
- `pytest-asyncio==0.23.3`
- `pytest-cov==4.1.0`
- `httpx==0.26.0`

**Monitoring:**
- `prometheus-client==0.19.0`
- `prometheus-fastapi-instrumentator==6.1.0`

**Logging:**
- `python-json-logger==2.0.7`

**Other:**
- `python-multipart==0.0.6`
- `python-dotenv==1.0.0`
- `redis==5.0.1`
- `aiokafka==0.10.0`
- `httpx==0.26.0` (для LLM requests)

**ФАЙЛ 2: `SETUP.md`** (Инструкции по развёртыванию)

**Требования:**

Создай подробную документацию с разделами:

1. **Prerequisites:**
   - Docker Desktop 4.20+
   - Python 3.11+
   - Git
   - AWS CLI (для S3)
   - kubectl (для production)

2. **Local Development Setup:**
   ```bash
   # Clone repository
   git clone https://github.com/your-org/email-intelligence-platform
   cd email-intelligence-platform
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy .env.example to .env
   cp .env.example .env
   
   # Edit .env with your settings
   nano .env
   ```

3. **Database Setup:**
   ```bash
   # Start PostgreSQL via Docker
   docker-compose up -d postgres
   
   # Wait for postgres to be ready
   docker-compose exec postgres pg_isready -U email_user
   
   # Apply migrations
   docker-compose exec postgres psql -U email_user -d email_db -f /docker-entrypoint-initdb.d/001_init_schema.sql
   
   # Verify tables created
   docker-compose exec postgres psql -U email_user -d email_db -c "\dt"
   ```

4. **Run Application:**
   ```bash
   # Start all services
   docker-compose up -d
   
   # Check all containers are healthy
   docker-compose ps
   
   # View logs
   docker-compose logs -f email-service
   
   # Test API
   curl http://localhost:8000/health
   ```

5. **Run Tests:**
   ```bash
   # Install dev dependencies
   pip install -r requirements-dev.txt
   
   # Run unit tests
   pytest tests/test_email_parser.py -v
   
   # Run integration tests
   pytest tests/test_integration.py -v
   
   # Run all tests with coverage
   pytest -v --cov=app --cov-report=html
   
   # Open coverage report
   open htmlcov/index.html
   ```

6. **Production Deployment (Kubernetes):**
   ```bash
   # Create namespace
   kubectl create namespace email-platform
   
   # Apply ConfigMaps
   kubectl apply -f k8s/configmap.yml
   
   # Apply Secrets (edit first!)
   kubectl apply -f k8s/secrets.yml
   
   # Deploy PostgreSQL
   kubectl apply -f k8s/postgres-deployment.yml
   
   # Deploy email-service
   kubectl apply -f k8s/email-service-deployment.yml
   
   # Check pods
   kubectl get pods -n email-platform
   
   # Check logs
   kubectl logs -f deployment/email-service -n email-platform
   ```

7. **Monitoring:**
   ```bash
   # Access Grafana
   kubectl port-forward svc/grafana 3000:3000 -n email-platform
   # Open http://localhost:3000 (admin/admin)
   
   # Access Prometheus
   kubectl port-forward svc/prometheus 9090:9090 -n email-platform
   # Open http://localhost:9090
   ```

8. **Troubleshooting:**
   - Problem: Database connection failed
     - Solution: Check DATABASE_URL in .env
   - Problem: S3 upload fails
     - Solution: Check AWS credentials and bucket permissions
   - Problem: LLM classification slow
     - Solution: Increase Ollama resources in docker-compose.yml

9. **Environment Variables:**
   ```bash
   # Required
   DATABASE_URL=postgresql+asyncpg://email_user:email_pass@localhost:5432/email_db
   S3_BUCKET=email-attachments
   
   # Optional
   OLLAMA_URL=http://localhost:11434
   LOG_LEVEL=INFO
   REDIS_URL=redis://localhost:6379
   KAFKA_BROKERS=localhost:9092
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```

10. **Next Steps:**
    - Configure LLM model: `docker exec -it ollama ollama pull llama3.1`
    - Create S3 bucket: `aws s3 mb s3://email-attachments`
    - Setup monitoring alerts: See `docs/issues/TZ-PHASE1-002-ALERTMANAGER.md`
    - Run E2E tests: `pytest tests/test_e2e.py`

**ВАЖНО:**
- Все bash команды должны быть протестированы
- Включи troubleshooting секцию
- Добавь примеры .env файла
- Укажи минимальные требования к ресурсам

**Ожидаемый размер:** ~45 строк requirements.txt + ~100 строк SETUP.md

Сгенерируй 2 файла:
1. requirements.txt (все зависимости с версиями)
2. SETUP.md (подробные инструкции)
```

---

**Проверка:**
После генерации убедитесь, что:
- ✅ requirements.txt содержит все зависимости с версиями
- ✅ SETUP.md содержит пошаговые инструкции для:
  - Local development
  - Database setup
  - Running tests
  - Production deployment
  - Troubleshooting

---

## 🎉 ПОЗДРАВЛЯЕМ!

После выполнения всех 8 команд у вас будет:

```
email-service/
├── migrations/
│   └── 001_init_schema.sql       # ✅ КОМАНДА 1 (350 lines)
├── app/
│   ├── models/
│   │   └── email_models.py       # ✅ КОМАНДА 2 (200 lines)
│   ├── services/
│   │   ├── email_parser.py       # ✅ КОМАНДА 3 (250 lines)
│   │   └── database.py           # ✅ КОМАНДА 4 (200 lines)
│   └── main.py                   # ✅ КОМАНДА 5 (200 lines)
├── tests/
│   ├── conftest.py               # ✅ КОМАНДА 6 (50 lines)
│   ├── test_email_parser.py      # ✅ КОМАНДА 6 (100 lines)
│   └── test_integration.py       # ✅ КОМАНДА 6 (100 lines)
├── Dockerfile                     # ✅ КОМАНДА 7 (40 lines)
├── docker-compose.yml             # ✅ КОМАНДА 7 (150 lines)
├── requirements.txt               # ✅ КОМАНДА 8 (45 lines)
└── SETUP.md                       # ✅ КОМАНДА 8 (100 lines)
```

**ИТОГО: 1,735 строк production-ready кода за 2-3 часа!**

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

1. **Запустите сервисы:**
   ```bash
   docker-compose up -d
   docker-compose ps  # Все должны быть healthy
   ```

2. **Примените миграции:**
   ```bash
   docker-compose exec postgres psql -U email_user -d email_db -f /docker-entrypoint-initdb.d/001_init_schema.sql
   ```

3. **Запустите тесты:**
   ```bash
   pytest -v --cov=app --cov-report=term-missing
   ```

4. **Проверьте API:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/metrics
   ```

5. **Изучите документацию:**
   - Прочитайте `SETUP.md` для production deployment
   - Изучите `docs/issues/README_PHASE1_TZ.md` для Phase 1 roadmap

---

**Последнее обновление:** 15 декабря 2025 г.  
**Версия:** 1.0.0  
**Автор:** Email Intelligence Platform Team  
**Лицензия:** MIT
