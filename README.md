# 🎓 AI Smart College Management & Student Intelligence System
### *Enterprise-Grade Core Backend Engine, Predictive ML Pipelines & Multimodal RAG Knowledge Architecture*

---

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B%20%7C%20pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7%2B%20%7C%20RQ%20Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20%2F%203.7%20Flash-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.9.1-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![WebSockets](https://img.shields.io/badge/WebSocket-Full%20Duplex%20Realtime-010101?style=for-the-badge&logo=socketdotio&logoColor=white)](https://websockets.readthedocs.io/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Institutional-blueviolet?style=for-the-badge)](#)

---

## 📖 Executive Architectural Overview

The **AI Smart College Management & Student Intelligence System** backend is an asynchronous, high-throughput higher education Enterprise Resource Planning (ERP) platform and autonomous academic intelligence engine. 

Engineered with **FastAPI**, **PostgreSQL with `pgvector`**, **Redis**, **LangChain**, and **Google Generative AI**, the system unifies complete institutional administrative operations—academic governance, admissions, fee ledgers, automated library circulation, and student lifecycle tracking—with state-of-the-art predictive machine learning and cognitive intelligence:

1. **Autonomous Institutional AI Assistant**: A role-scoped LangChain agent powered by Google Gemini (2.0 / 3.7 Flash) that intelligently queries PostgreSQL relational tables and institutional policy vectors to provide context-aware, auditable answers with source citations.
2. **Multimodal RAG Knowledge Engine**: High-performance document processing pipeline ingesting PDF, DOCX, and scanned image documents via **PyTesseract OCR** and **PyMuPDF**, generating 768-dimensional embeddings via Google `text-embedding-004`, indexed in PostgreSQL via `pgvector` cosine similarity with Redis semantic response caching.
3. **Student Early-Warning & Predictive Analytics Engine**: Automated machine learning pipelines computing dropout risks, K-Means student cohort segmentation, GPA trajectory forecasting, and automated remediation recommendations run via background **APScheduler** cron jobs.
4. **Real-Time Campus WebSocket Network**: Full-duplex WebSocket messaging engine with connection pooling across multiple devices and tabs, presence tracking, typing indicators, delivery/read receipts, and academic communication guardrails.
5. **7-Tier Institutional Role-Based Access Control (RBAC)**: Strict cryptographic JWT authorization isolating capabilities between Admin, HOD, Faculty, Student, Accountant, Librarian, and Admission Officer roles.

---

## 🏛️ System Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["API Consumers & Clients"]
        WEB["Desktop / Web Frontend"]
        MOB["Mobile Applications"]
        EXT["External Institutional APIs"]
    end

    subgraph Gateway["API Gateway & Transport Layer"]
        UVICORN["Uvicorn ASGI Engine (127.0.0.1:8000)"]
        CORS["CORS Middleware"]
        SECURITY["JWT RBAC Authentication Guard"]
    end

    subgraph FastAPICore["FastAPI Application Core (app/main.py)"]
        R_AUTH["Auth Router (/auth)"]
        R_ACAD["Academic Routers (/hod, /faculty, /dept, /courses, /subjects)"]
        R_STUD["Student Lifecycle (/students, /attendance, /marks, /performance)"]
        R_OPS["Operational Routers (/admissions, /fees, /library)"]
        R_ML["Intelligence Routers (/risk, /predictions, /segmentation, /recommendations)"]
        R_AI["AI Services (/ai, /rag-documents)"]
        R_WS["Real-Time Campus Chat (/chat, /chat/ws)"]
    end

    subgraph ServiceEngine["Service Layer & AI / ML Pipelines"]
        WS_MGR["WebSocket Connection Manager (chat_manager.py)"]
        AI_AGENT["LangChain Gemini Agent + SQL Tools (ai_assistant.py)"]
        RAG_ENG["Multimodal RAG Pipeline (rag_service.py)"]
        ML_PIPE["Predictive Risk & Segmentation Engine (ml_dataset_service.py)"]
    end

    subgraph StorageLayer["Data & Persistence Tier"]
        PG[("PostgreSQL 16 Relational Engine")]
        PGV[("pgvector Vector Store (vector_768)")]
        REDIS[("Redis 7: Caching & PubSub")]
        RQ_Q[("Redis RQ Task Queue")]
    end

    subgraph AsynchronousWorkers["Asynchronous Background Workers"]
        RQ_WORKER["RAG Ingestion Worker (rag_worker.py)"]
        TESSERACT["PyTesseract OCR + PyMuPDF"]
        AP_SCHED["APScheduler: Nightly ML Model Recalibration"]
    end

    WEB & MOB & EXT --> UVICORN
    UVICORN --> CORS --> SECURITY
    SECURITY --> R_AUTH & R_ACAD & R_STUD & R_OPS & R_ML & R_AI & R_WS

    R_WS <--> WS_MGR
    R_AI --> AI_AGENT
    R_AI --> RAG_ENG
    R_ML --> ML_PIPE

    R_ACAD & R_STUD & R_OPS & R_AUTH --> PG
    AI_AGENT -->|Dynamic SQL Tools| PG
    AI_AGENT -->|Semantic Context| PGV
    RAG_ENG -->|Semantic Search| PGV
    RAG_ENG -->|Cache Hit / Miss| REDIS
    RAG_ENG -->|Submit Ingestion Job| RQ_Q

    RQ_Q --> RQ_WORKER
    RQ_WORKER --> TESSERACT
    TESSERACT -->|Store Chunks & Embeddings| PGV
    FastAPICore --> AP_SCHED
    AP_SCHED -->|Daily Risk & Cluster Updates| PG
```

---

## 🛠️ Technology Stack & Dependencies

| Layer | Technology | Version | Purpose in System |
| :--- | :--- | :--- | :--- |
| **Core Framework** | `FastAPI` | `0.141.1` | High-performance asynchronous REST API framework |
| **ASGI Server** | `Uvicorn` | `0.52.4` | Production ASGI web server runninguvloop event loop |
| **Database Engine** | `PostgreSQL` | `16+` | Primary ACID relational database for all institutional entities |
| **Vector Database** | `pgvector` | `0.5.1` | Native vector extension for cosine similarity search (`<=>`) |
| **ORM & Migrations**| `SQLAlchemy` | `2.0.52` | Python Object Relational Mapper for model and transaction management |
| **Database Driver** | `psycopg2-binary` | `2.9.13` | High-performance PostgreSQL database adapter |
| **In-Memory Cache** | `Redis` | `8.1.0` | 300-second semantic query cache, connection states, and session storage |
| **Task Queue** | `RQ (Redis Queue)`| `2.12.0` | Asynchronous job execution for compute-heavy document processing |
| **Job Scheduler** | `APScheduler` | `3.11.3` | Scheduled cron engine for periodic ML model training and risk recalibration |
| **LLM Orchestration**| `Google GenAI` / `LangChain` | `2.24.0` / `1.4.1` | Gemini 2.0 / 3.7 Flash agent execution and dynamic tool chaining |
| **Vector Embeddings**| `text-embedding-004` | Google GenAI | 768-dimensional dense vector embeddings for policy and curriculum RAG |
| **Machine Learning**| `scikit-learn` | `1.9.1` | K-Means clustering, logistic regression, and predictive academic modeling |
| **Scientific Compute**| `NumPy` / `Pandas` | `2.5.3` / `3.0.5` | Academic dataset extraction, vector manipulation, and feature engineering |
| **Document Parsing**| `PyMuPDF (fitz)` / `python-docx` | `2.0` / `1.2.0` | High-fidelity PDF layout extraction, text splitting, and Word doc parsing |
| **Optical Character Recognition** | `pytesseract` / `Pillow` | `0.3.13` / `13.0.0` | Deep OCR processing for scanned institutional notices and marksheets |
| **Real-Time WebSockets** | `websockets` / `FastAPI` | `16.1.1` | Low-latency duplex messaging, typing events, and read receipts |
| **Auth & Cryptography**| `python-jose` / `passlib` / `bcrypt` | `3.5.0` / `1.7.4` | HMAC-SHA256 JWT tokens and salted Bcrypt password hashing |

---

## 🗄️ Database Architecture & Data Models (35 Models)

The data tier is engineered using SQLAlchemy 2.0 and structured into 8 modular relational domains:

```
app/database/models.py
```

```mermaid
erDiagram
    User ||--o{ HOD : "heads"
    User ||--o{ Faculty : "profile"
    User ||--o{ Student : "profile"
    User ||--o{ Accountant : "profile"
    User ||--o{ Librarian : "profile"
    User ||--o{ AdmissionOfficer : "profile"

    Department ||--o{ Course : "offers"
    Department ||--o{ Faculty : "employs"
    Department ||--o{ Student : "enrolls"
    Course ||--o{ Subject : "contains"
    Faculty ||--o{ FacultySubject : "teaches"
    Subject ||--o{ FacultySubject : "assigned_to"

    Student ||--o{ Attendance : "logs"
    Student ||--o{ Marks : "scores"
    Student ||--o{ Assignment : "submits"
    Student ||--o{ Performance : "evaluates"
    Student ||--o{ StudentRisk : "profiled_by"
    Student ||--o{ Prediction : "forecasts"
    Student ||--o{ Recommendation : "advised_by"
    Student ||--o{ StudentFee : "billed"

    FeeStructure ||--o{ StudentFee : "defines"
    StudentFee ||--o{ FeePayment : "paid_via"
    FeePayment ||--o{ FeeRefund : "refunded"

    Book ||--o{ BookCopy : "inventory"
    BookCopy ||--o{ BookIssue : "circulated"
    BookIssue ||--o{ LibraryFine : "accrues"
    LibraryFine ||--o{ LibraryFinePayment : "cleared_by"

    ChatConversation ||--o{ ChatParticipant : "members"
    ChatConversation ||--o{ ChatMessage : "messages"
    ChatMessage ||--o{ ChatMessageReceipt : "receipts"
    ChatMessage ||--o{ ChatMessageDeletion : "soft_deletes"
```

### 1. Identity & Role-Based Access Control (RBAC)
* **`User`** (`users`): Primary identity entity. Fields: `id`, `name`, `email`, `password_hash`, `role` (`admin`, `hod`, `faculty`, `student`, `accountant`, `librarian`, `admission_officer`), `is_active`, `created_at`.
* **`HOD`** (`hods`): Department head profile linked to `User` and `Department`.
* **`Faculty`** (`faculties`): Faculty profile linked to `User` and `Department`. Fields: `qualification`, `designation`, `experience_years`.
* **`Student`** (`students`): Core student record linked to `User`, `Department`, and `Course`. Fields: `roll_number`, `enrollment_number`, `current_semester`, `admission_date`, `status`.
* **`Accountant`** (`accountants`): Bursar/finance staff profile linked to `User`.
* **`Librarian`** (`librarians`): Library administration profile linked to `User`.
* **`AdmissionOfficer`** (`admission_officers`): Admissions intake administrator profile linked to `User`.

### 2. Academic Hierarchy & Curriculum
* **`Department`** (`departments`): Academic branch (e.g., Computer Science, Electrical).
* **`Course`** (`courses`): Degree programs (e.g., B.Tech, M.Tech, BCA) under a Department.
* **`Subject`** (`subjects`): Individual credit-bearing modules. Fields: `code`, `name`, `credits`, `semester`.
* **`FacultySubject`** (`faculty_subjects`): Many-to-many junction mapping faculty teaching assignments to specific subjects and semesters.
* **`StudentSemesterHistory`** (`student_semester_history`): Historical audit log tracking semester transitions, academic status, and cumulative GPAs over time.

### 3. Academic Evaluation & Monitoring
* **`Attendance`** (`attendance`): Daily lecture attendance. Fields: `student_id`, `subject_id`, `date`, `status` (`Present`, `Absent`, `Late`), `marked_by_faculty_id`.
* **`Marks`** (`marks`): Exam scores. Fields: `student_id`, `subject_id`, `exam_type` (`internal`, `midterm`, `final`), `score`, `max_score`.
* **`Assignment`** (`assignments`): Coursework tracking. Fields: `title`, `subject_id`, `student_id`, `due_date`, `submission_status`, `score`.
* **`Performance`** (`performance`): Aggregate academic metrics. Fields: `student_id`, `semester`, `gpa`, `total_credits`, `attendance_percentage`.

### 4. Admissions Management
* **`AdmissionApplication`** (`admission_applications`): Applicant intake state machine. Fields: `applicant_name`, `email`, `phone`, `course_id`, `high_school_percentage`, `status` (`submitted`, `under_review`, `approved`, `rejected`, `enrolled`), `processed_by`.

### 5. Financial Management & Fee Ledgers
* **`FeeStructure`** (`fee_structures`): Tariff schedule defining total tuition, laboratory, and library fees per department, course, and semester.
* **`StudentFee`** (`student_fees`): Active student fee ledger. Fields: `student_id`, `fee_structure_id`, `amount_due`, `amount_paid`, `status` (`unpaid`, `partial`, `paid`).
* **`FeePayment`** (`fee_payments`): Immutable transaction logs. Fields: `receipt_number`, `amount`, `payment_method` (`cash`, `upi`, `card`, `netbanking`), `transaction_reference`, `recorded_by`.
* **`FeeRefund`** (`fee_refunds`): Fee reversal and refund auditing.

### 6. Automated Library Circulation
* **`Book`** (`books`): Catalog master record. Fields: `title`, `author`, `isbn`, `edition`, `category`.
* **`BookCopy`** (`book_copies`): Physical inventory tracking with unique barcode/accession identifiers.
* **`BookIssue`** (`book_issues`): Circulation register. Fields: `book_copy_id`, `student_id`, `issue_date`, `due_date`, `return_date`, `status` (`issued`, `returned`, `overdue`).
* **`LibraryFine`** (`library_fines`): Automated overdue penalty calculator. Fields: `amount`, `status` (`pending`, `paid`).
* **`LibraryFinePayment`** (`library_fine_payments`): Overdue fine settlement audit logs.

### 7. Machine Learning & Risk Intelligence
* **`StudentRisk`** (`student_risks`): Dropout early-warning indicators. Fields: `student_id`, `risk_level` (`Low`, `Medium`, `High`), `risk_score` (0.0-1.0), `risk_factors` (JSON), `updated_at`.
* **`Prediction`** (`predictions`): Academic performance forecast. Fields: `predicted_gpa`, `pass_probability`, `target_semester`.
* **`Recommendation`** (`recommendations`): Actionable AI-generated remedial steps. Fields: `type`, `description`, `is_actioned`.
* **`StudentMLRecord`** (`student_ml_records`): Normalized numerical feature vectors cached for training Scikit-Learn models.

### 8. Campus Real-Time Chat Network
* **`ChatConversation`** (`chat_conversations`): Direct (1-on-1) and Group chat rooms. Fields: `type` (`direct`, `group`), `title`, `created_by`.
* **`ChatParticipant`** (`chat_participants`): Membership roster. Fields: `conversation_id`, `user_id`, `role` (`admin`, `member`), `last_read_message_id`, `unread_count`.
* **`ChatMessage`** (`chat_messages`): Message payloads. Fields: `conversation_id`, `sender_id`, `content`, `attachment_url`, `created_at`.
* **`ChatMessageReceipt`** (`chat_message_receipts`): Granular delivery and read confirmations per user.
* **`ChatMessageDeletion`** (`chat_message_deletions`): Soft deletion records supporting "delete for me" and "delete for everyone".

---

## 🌐 API Architecture & Endpoint Directory (24 Routers)

All routers are mounted in `app/main.py` with automatic OpenAPI specification available at `/docs` and `/redoc`.

```
app/routers/
├── auth.py              # Authentication, JWT issuance, profile
├── admission.py         # Application intake, review workflows
├── fee.py               # Fee structures, invoicing, payment verification
├── library.py           # Catalog, barcode circulation, fines
├── hod.py               # Departmental analytics, faculty oversight
├── department.py        # Department administration
├── faculty.py           # Faculty directory & workload
├── student.py           # Student enrollment & records
├── course.py            # Course catalog
├── subject.py           # Subject curriculum & credit weighting
├── faculty_subject.py   # Teaching workload allocations
├── attendance.py        # Lecture attendance marking & aggregation
├── marks.py             # Examination score recording & grades
├── assignment.py        # Assignment lifecycle & grading
├── performance.py       # Transcripts, GPA/CGPA computation
├── risk.py              # Early warning dropout classification
├── prediction.py        # Predictive GPA & pass/fail forecasting
├── segmentation.py      # Student K-Means clustering cohorts
├── recommendation.py    # AI remedial guidance generation
├── rag_documents.py     # Multimodal document ingestion & vector search
├── ai_assistant.py      # Conversational SQL agent & policy retrieval
├── chat.py              # REST chat operations & WebSocket transport
├── dashboard.py         # Role-specific operational KPI metrics
└── intelligence.py      # Cross-institutional predictive summaries
```

### Detailed Endpoint Catalog

#### 1. Authentication & Identity (`/auth`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Public | Authenticates credentials and returns JWT bearer token |
| `POST` | `/auth/register` | Admin | Registers institutional users with explicit role designation |
| `GET` | `/auth/me` | Authenticated | Retrieves profile metadata for the authenticated token |

#### 2. Admission Management (`/admissions`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/admissions/apply` | Public / Officer | Submits new candidate admission application |
| `GET` | `/admissions/` | Admin, Admission Officer | Lists applications with status and course filters |
| `PATCH` | `/admissions/{id}/status` | Admin, Admission Officer | Updates application state (`under_review`, `approved`, `rejected`) |
| `POST` | `/admissions/{id}/enroll` | Admin, Admission Officer | Converts approved application into an active `Student` and `User` |

#### 3. Fee Engine & Financial Ledgers (`/fees`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/fees/structures` | Admin, Accountant | Configures fee tariff for course and semester |
| `GET` | `/fees/student/{student_id}`| Admin, Accountant, Student | Retrieves fee dues, payments, and balance ledger |
| `POST` | `/fees/payments` | Admin, Accountant | Records payment, updates student ledger, and generates receipt |
| `POST` | `/fees/refunds` | Admin, Accountant | Processes verified fee refund transactions |

#### 4. Automated Library Circulation (`/library`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/library/books` | Admin, Librarian | Registers master book record with ISBN and copies |
| `POST` | `/library/issue` | Admin, Librarian | Issues book copy to student with calculated due date |
| `POST` | `/library/return` | Admin, Librarian | Returns book copy and calculates overdue penalties |
| `POST` | `/library/fines/{id}/pay` | Admin, Librarian, Accountant | Settles outstanding overdue library fines |

#### 5. Academic Governance & Curriculum (`/hod`, `/departments`, `/courses`, `/subjects`, `/faculties`, `/faculty-subjects`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/hod/dashboard` | HOD | Retrieves department-scoped performance and attendance metrics |
| `POST` | `/departments/` | Admin | Creates academic department |
| `POST` | `/courses/` | Admin | Registers degree program under a department |
| `POST` | `/subjects/` | Admin, HOD | Creates subject with credit value and semester |
| `POST` | `/faculty-subjects/assign`| Admin, HOD | Allots teaching responsibility to faculty member |

#### 6. Student Lifecycle & Academic Performance (`/students`, `/attendance`, `/marks`, `/assignments`, `/performance`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/students/` | Admin, HOD, Faculty | Retrieves paginated student directory with department filters |
| `POST` | `/attendance/mark` | Faculty, HOD | Submits batch lecture attendance records |
| `GET` | `/attendance/student/{id}`| Authenticated | Retrieves subject-wise attendance percentages |
| `POST` | `/marks/submit` | Faculty, HOD | Records internal, midterm, and end-term exam marks |
| `GET` | `/performance/{student_id}`| Authenticated | Generates comprehensive transcript with calculated GPA/CGPA |

#### 7. Predictive Analytics & Machine Learning (`/risk`, `/predictions`, `/segmentation`, `/recommendations`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/risk/students` | Admin, HOD, Faculty | Lists students classified by dropout risk tier (High / Medium / Low) |
| `POST` | `/risk/recalculate` | Admin | Triggers immediate risk scoring recalculation |
| `GET` | `/predictions/gpa/{student_id}` | Authenticated | Generates forecasted end-of-semester GPA projection |
| `GET` | `/segmentation/clusters` | Admin, HOD | Returns K-Means student cohorts with centroid descriptors |
| `GET` | `/recommendations/{student_id}`| Authenticated | Generates AI-assisted remediation and improvement roadmap |

#### 8. Multimodal RAG Knowledge Engine (`/rag-documents`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/rag-documents/upload` | Admin | Uploads PDF, DOCX, or scanned images (up to 20MB) for background ingestion |
| `POST` | `/rag-documents/process-all` | Admin | Enqueues unprocessed documents into the Redis RQ worker |
| `GET` | `/rag-documents/jobs/{job_id}`| Admin | Returns background job status and vectorization progress |
| `GET` | `/rag-documents/jobs/{job_id}/stream` | Admin | Server-Sent Events (SSE) real-time vectorization progress stream |
| `POST` | `/rag-documents/search` | Authenticated | Performs cosine similarity search over institutional vector chunks |

#### 9. Autonomous AI College Assistant (`/ai`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/ai/ask` | Authenticated | Submits query to LangChain agent; returns answers with source citations |
| `GET` | `/ai/capabilities` | Authenticated | Lists available SQL tools based on user's institutional role |

#### 10. Campus Real-Time Chat & Collaboration (`/chat`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/chat/users` | Authenticated | Returns directory of users eligible for chat under academic rules |
| `POST` | `/chat/direct/{user_id}` | Authenticated | Initiates or returns an existing 1-on-1 direct conversation |
| `POST` | `/chat/group` | Authenticated | Creates multi-user group chat with title and participants |
| `GET` | `/chat/conversations` | Authenticated | Lists conversations with unread counts and latest messages |
| `GET` | `/chat/conversations/{id}/messages` | Authenticated | Fetches paginated chat message history |
| `POST` | `/chat/conversations/{id}/read` | Authenticated | Marks all unread messages as read and broadcasts read receipt |
| `DELETE`| `/chat/messages/{message_id}` | Authenticated | Soft-deletes message ("for me" or "for everyone") |
| `WSS` | `/chat/ws/{conversation_id}` | Authenticated (Token) | Full-duplex WebSocket connection for real-time messaging |

#### 11. Dashboards & Institutional Intelligence (`/dashboard`, `/intelligence`)
| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/dashboard/metrics` | Authenticated | Role-tailored metrics (Admissions, Fees, Attendance, Library) |
| `GET` | `/intelligence/summary`| Admin, HOD | Cross-departmental predictive intelligence and risk distributions |

---

## 🤖 Deep Dive: Autonomous AI College Assistant & Dynamic SQL Agent

The AI Assistant (`app/services/ai_assistant.py`) is an autonomous, agentic system built using **LangChain** and **Google Gemini 2.0 / 3.7 Flash**.

```mermaid
flowchart TD
    UserQuery["User Natural Language Question"] --> Classifier{"Query Classifier"}
    
    Classifier -->|Policy / Document Inquiries| RAGSearch["PostgreSQL pgvector Semantic Search"]
    Classifier -->|Database / Statistical Inquiries| SQLTools["Role-Scoped Dynamic SQL Agent"]
    Classifier -->|Hybrid Inquiries| HybridEngine["Combined Context Assembler"]

    subgraph DynamicRBACGuards["Tool Authorization Barrier"]
        SQLTools --> RoleCheck{"Check User Role"}
        RoleCheck -->|Student| S_Tool["get_my_attendance, get_my_marks, get_my_fees"]
        RoleCheck -->|Faculty| F_Tool["get_class_attendance, get_subject_marks"]
        RoleCheck -->|HOD| H_Tool["get_department_kpis, get_faculty_workload"]
        RoleCheck -->|Admin| A_Tool["System-Wide Analytics Tools"]
    end

    RAGSearch --> ContextAssembler["Context Synthesizer with Source Chunks"]
    SQLTools --> ContextAssembler
    HybridEngine --> ContextAssembler

    ContextAssembler --> GeminiLLM["Gemini 2.0 / 3.7 Flash Engine"]
    GeminiLLM --> CitationParser["Citation Validator (Regex [Source: ...])"]
    CitationParser --> VerifiedResponse["Auditable Response + Cited Sources"]
```

### 1. Multi-Stage Question Routing
Incoming queries are classified into four processing modes:
* `database_only`: Direct queries regarding attendance records, grades, fee receipts, or syllabus schedules routed to dynamic SQL agent tools.
* `policy_only`: Queries regarding institutional regulations, admission guidelines, grading scales, or codes of conduct routed to vector search.
* `combined`: Questions requiring both relational database values and official college documentation.
* `general`: Casual academic conversation handled directly by the LLM system prompt.

### 2. Role-Enforced Dynamic SQL Tools (`app/services/ai_tools.py`)
To prevent data leakage, the agent does **not** possess open SQL execution privileges. Instead, it is equipped with explicit, strictly typed, parameter-validated Python functions that execute authorized queries:
* **Student Tools**: `get_my_attendance(student_id)`, `get_my_fee_status(student_id)`, `get_my_marks(student_id)`.
* **Faculty Tools**: `get_class_attendance_summary(subject_id)`, `get_subject_grade_distribution(subject_id)`.
* **HOD Tools**: `get_department_faculty_metrics(dept_id)`, `get_department_at_risk_students(dept_id)`.
* **Admin Tools**: `get_institutional_financial_summary()`, `get_admission_pipeline_metrics()`.

### 3. Strict Source Attribution Engine
The system enforces auditable transparency:
* Chunks returned by vector search are tagged with `[Source: <filename> (chunk <number>)]`.
* A post-processing regex parser (`get_cited_sources()`) verifies that only documents actually cited in the LLM's final response are returned in the response metadata.

---

## 📄 Deep Dive: Multimodal RAG Engine (Retrieval-Augmented Generation)

The RAG engine (`app/services/rag_service.py` & `app/workers/rag_worker.py`) is an asynchronous document processing and retrieval pipeline.

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant API as FastAPI (/rag-documents)
    participant RedisQ as Redis RQ Task Queue
    participant Worker as Background RQ Worker
    participant OCR as PyMuPDF & PyTesseract
    participant GenAI as Google GenAI (text-embedding-004)
    participant PGV as PostgreSQL (pgvector)
    participant Cache as Redis 7 Cache

    Admin->>API: Upload Document (.pdf, .docx, .png, .jpg)
    API->>API: Validate MIME & Size (<= 20MB)
    API->>RedisQ: Enqueue Ingestion Job (job_id)
    API-->>Admin: Return job_id (202 Accepted)
    
    Worker->>RedisQ: Pop Job
    Worker->>OCR: Extract Text & Apply OCR on Scanned Pages
    OCR-->>Worker: Raw Text Stream
    Worker->>Worker: Chunk Text (Overlap: 100, ChunkSize: 1000)
    Worker->>GenAI: Request 768d Vector Embeddings
    GenAI-->>Worker: Dense Embeddings Array
    Worker->>PGV: Store Chunks & Vector Records
    Worker-->>RedisQ: Mark Job Complete

    Note over API,Cache: Query Time
    actor User
    User->>API: Natural Language Question
    API->>Cache: Check Semantic Query Cache
    alt Cache Hit
        Cache-->>API: Return Cached Chunks & Response
    else Cache Miss
        API->>GenAI: Generate Query Embedding
        GenAI-->>API: 768d Query Vector
        API->>PGV: Execute Cosine Search (<=> Operator)
        PGV-->>API: Top-K Vector Chunks
        API->>Cache: Store in Cache (TTL = 300s)
    end
    API-->>User: Return Retrieved Knowledge Chunks
```

### Key Technical Specifications
1. **Multimodal Extraction Pipeline**:
   * **PDF Documents**: Parsed using PyMuPDF (`fitz`) for fast text extraction. Scanned pages or embedded diagrams are automatically routed to PyTesseract OCR.
   * **Word Documents**: Parsed with `python-docx` preserving paragraph structure and tables.
   * **Images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`)**: Preprocessed with Pillow (contrast normalization) and processed via Tesseract OCR engine.
2. **Asynchronous Redis Queue (RQ) Architecture**:
   * Heavy OCR and vectorization tasks run outside the web request cycle via `app/workers/rag_worker.py`.
   * Real-time progress is broadcasted to the frontend via Server-Sent Events (`GET /rag-documents/jobs/{job_id}/stream`).
3. **High-Dimensional Vector Space (`pgvector`)**:
   * Embeddings model: Google `text-embedding-004`.
   * Dimension: `768`.
   * Similarity metric: Cosine distance using the `<=>` vector index operator.
4. **Redis Semantic Caching**:
   * Repeated queries are cached with a 300-second TTL (`RAG_CACHE_TTL_SECONDS = 300`), eliminating redundant LLM API calls and reducing response latency to `< 15ms`.

---

## 🧠 Deep Dive: Predictive Machine Learning Pipelines

The predictive suite operates across multiple analytical dimensions to track student progression and prevent dropouts before they occur.

```mermaid
flowchart LR
    subgraph DataExtraction["Data Ingestion Engine"]
        A1["Attendance Logs"] --> F_ENG["Feature Engineering Pipeline (ml_dataset_service.py)"]
        A2["Exam Marks & GPAs"] --> F_ENG
        A3["Assignment Submissions"] --> F_ENG
        A4["Fee Payment Timelines"] --> F_ENG
    end

    subgraph FeatureStore["Normalized Feature Store"]
        F_ENG --> VEC["Feature Vector: [att_rate, gpa_drift, late_assign_ratio, fee_delinquency]"]
    end

    subgraph PredictiveModels["Scikit-Learn ML Engines"]
        VEC --> RISK["Dropout Early-Warning Classifier (prediction_service.py)"]
        VEC --> CLUST["K-Means Cohort Segmentation (segmentation_service.py)"]
        VEC --> TRAJ["GPA Trajectory Model (future_prediction_model.py)"]
    end

    subgraph Intervention["Automated Interventions"]
        RISK -->|High Risk Flag| REC["Remedial Recommendation Engine (recommendation_service.py)"]
        CLUST -->|Cluster Persona| ADVISOR["Advisor Notification"]
        TRAJ -->|Predicted GPA Decline| TUTOR["Assigned Remedial Class"]
    end
```

### 1. Dropout Risk Early-Warning Classifier (`prediction_service.py`)
* Analyzes multidimensional risk indicators:
  * Attendance drop rate below institutional thresholds (e.g., `< 75%`).
  * Grade trajectories across successive internal assessments.
  * Fee payment delinquency and financial stress patterns.
  * Homework and assignment submission velocity.
* Categorizes each student into **Low**, **Medium**, or **High** risk tiers, storing actionable factor breakdowns in `student_risks.risk_factors`.

### 2. K-Means Cohort Segmentation (`segmentation_service.py`)
* Unsupervised K-Means clustering partitions the student body into actionable behavioural cohorts:
  * *High-Velocity Achievers*: High attendance, consistent high scores, early submissions.
  * *Inconsistent Performers*: High exam scores but poor attendance or sporadic submissions.
  * *Struggling Students*: Low attendance, failing grades, requiring active academic intervention.
* Provides department heads and deans with macroscopic cohort distributions.

### 3. Future GPA Trajectory Forecasting (`future_prediction_model.py`)
* Employs linear trend projection and historical semester regression to forecast the student's end-of-semester GPA.
* Identifies students whose trajectory is dropping significantly compared to their cumulative GPA.

### 4. Automated Background Scheduling (`ml_scheduler.py`)
* Utilizes **APScheduler** (`BackgroundScheduler`) to automatically trigger feature extraction, model inference, and database persistence on a nightly schedule without manual intervention.

---

## ⚡ Deep Dive: Real-Time WebSocket Campus Chat System

The campus chat subsystem (`app/routers/chat.py` & `app/services/chat_manager.py`) provides real-time, bidirectional messaging between campus constituents.

```mermaid
sequenceDiagram
    autonumber
    participant Alice as Alice (Student - Browser Tab 1)
    participant Alice2 as Alice (Student - Mobile App)
    participant WS as WebSocket Manager (chat_manager.py)
    participant DB as PostgreSQL Database
    participant Bob as Bob (Faculty Member)

    Alice->>WS: Connect: /chat/ws/42?token=JWT
    WS->>WS: Validate JWT, Check Permissions (is_chat_allowed)
    WS->>WS: Register connection in active_connections[42][Alice]
    WS-->>Alice: Connection Accepted

    Alice->>WS: Send JSON: {"type": "message", "content": "Hello Professor"}
    WS->>DB: Persist ChatMessage & Initialize ChatMessageReceipts
    
    par Multi-Device Broadcast to Sender
        WS-->>Alice: Echo message confirmation
        WS-->>Alice2: Broadcast to other active devices of Alice
    and Delivery to Recipient
        WS-->>Bob: Push message payload to Bob's active socket
    end

    Bob->>WS: Send JSON: {"type": "read_receipt", "message_id": 105}
    WS->>DB: Update ChatMessageReceipt (read_at = NOW())
    WS-->>Alice: Broadcast "message_read" event (Turn checks blue)
```

### 1. Connection Pool & Thread Safety
* Multi-device connection tracking: A single user can be logged in simultaneously on a phone, laptop, and tablet. The `ChatConnectionManager` maintains:
  * `active_connections[conversation_id][user_id] -> Set[WebSocket]`
  * `user_connections[user_id] -> Set[WebSocket]`
* Concurrency guard: Protected with Python's asynchronous locks (`asyncio.Lock`) to prevent race conditions during connection drops or simultaneous message emissions.

### 2. Institutional Academic Boundaries (`is_chat_allowed`)
* The chat engine enforces academic communication policies:
  * Students can only initiate conversations with faculty assigned to their active course subjects, their HOD, or peer students enrolled in their branch.
  * Unrelated direct messaging across unassigned academic branches is restricted.

### 3. Event Protocol
* `message`: Standard chat payload containing text or attachment URLs.
* `typing_start` / `typing_stop`: Ephemeral typing indicators broadcasted to active room members.
* `read_receipt`: Updates participant's `last_read_message_id` and emits read confirmations.
* `user_presence`: Online/offline status broadcasts.
* `delete_message`: Propagates deletion events across all active client sockets.

---

## 🔒 Enterprise Security, Authentication & RBAC

The system implements defence-in-depth security principles across transport, authentication, and data layers:

### 1. Password Hashing
* Uses **Passlib** with the **Bcrypt** algorithm. Passwords are never stored in plain text and are salted before hashing with high work factors.

### 2. Cryptographic JWT Token Architecture
* Authentication issues JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
* Tokens carry claims: `sub` (user email), `role` (institutional role), `user_id`, and `exp` (expiration timestamp).
* The application runs `validate_auth_config()` during server startup (`app/main.py`), preventing execution if insecure defaults or weak keys are detected.

### 3. Dependency Injection Security Guards (`app/utils/auth.py`)
All endpoints enforce declarative RBAC via FastAPI's `Depends()` dependency injection:
* `get_current_user`: Extracts, validates, and decodes the JWT bearer token.
* `require_admin`: Strictly permits users with `role == 'admin'`.
* `get_current_hod`: Restricts access to department heads and resolves their assigned department context.
* `require_faculty`: Ensures caller is an active faculty member.
* `require_student`: Restricts access to student self-service operations.
* `require_accountant`: Restricts financial ledger edits and fee approvals.
* `require_librarian`: Restricts book catalog modifications and circulation management.
* `require_admission_officer`: Restricts applicant state changes.

---

## ⚙️ Environment Configuration Reference (`.env`)

Create a `.env` file in the project root directory following this specification:

```ini
# ==============================================================================
# DATABASE CONFIGURATION (PostgreSQL 16+ with pgvector)
# ==============================================================================
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/ai_college_db

# ==============================================================================
# GOOGLE GENERATIVE AI (Gemini LLM & text-embedding-004)
# ==============================================================================
GEMINI_API_KEY=AIzaSyYourGeneratedGeminiApiKeyHere

# ==============================================================================
# OPTICAL CHARACTER RECOGNITION (Tesseract OCR Engine)
# ==============================================================================
# Windows default path:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
# Linux / Docker default path:
# TESSERACT_CMD=/usr/bin/tesseract

OCR_LANGUAGE=eng
RAG_VISION_ENABLED=true

# ==============================================================================
# SECURITY & CRYPTOGRAPHIC JWT CONFIGURATION
# ==============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=55d345aad09e5f49e393f45c63799c01822601bdb7129e84ae6390e9bb3cf0ba
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ==============================================================================
# REDIS CONFIGURATION (Cache, Task Queue, Session Management)
# ==============================================================================
REDIS_URL=redis://localhost:6379/0
```

### Parameter Description Table

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `DATABASE_URL` | **Yes** | — | SQLAlchemy connection string pointing to PostgreSQL database |
| `GEMINI_API_KEY` | **Yes** | — | Google AI Studio API key for Gemini 2.0 / 3.7 Flash and embeddings |
| `TESSERACT_CMD` | **Yes** | OS-dependent | Absolute file path to the Tesseract OCR executable binary |
| `OCR_LANGUAGE` | No | `eng` | Target language code for Tesseract OCR processing |
| `RAG_VISION_ENABLED` | No | `true` | Enables image document processing and visual OCR |
| `SECRET_KEY` | **Yes** | — | 256-bit secret key used to sign and verify JWT authentication tokens |
| `ALGORITHM` | No | `HS256` | Cryptographic signature algorithm for JWT encoding |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Token validity duration in minutes before refresh is required |
| `REDIS_URL` | **Yes** | `redis://localhost:6379/0` | Connection string for Redis cache and background RQ worker |

---

## 🚀 Local Installation & Setup Guide

### 1. Prerequisites
Ensure the following software packages are installed on your host machine:
* **Python**: Version `3.10` or higher (`python --version`)
* **PostgreSQL**: Version `16` or higher with administrative access
* **Redis**: Version `7.0` or higher (`redis-cli ping`)
* **Tesseract OCR**: 
  * *Windows*: Download and run the [UB-Mannheim Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki).
  * *Ubuntu/Debian*: `sudo apt update && sudo apt install -y tesseract-ocr`
  * *macOS*: `brew install tesseract`

---

### 2. Database Initialization & `pgvector` Setup
Connect to PostgreSQL and create the database with the `pgvector` extension enabled:

```sql
-- Connect via psql or PgAdmin
CREATE DATABASE ai_college_db;

-- Connect to the newly created database
\c ai_college_db;

-- Enable the pgvector extension for high-dimensional embeddings
CREATE EXTENSION IF NOT EXISTS vector;
```

---

### 3. Virtual Environment Setup & Dependencies
Clone the repository, initialize a Python virtual environment, and install dependencies:

```bash
# Clone the repository
git clone https://github.com/your-institution/ai-smart-college-system.git
cd ai-smart-college-system

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
call venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Upgrade pip and install all project dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Create Initial Super-Admin Account
Run the interactive database administrative seeding script:

```bash
python create_admin.py
```

Follow the CLI prompts:
```text
=== Create First Admin ===
Admin name: System Administrator
Admin email: admin@college.edu
Admin password: [SecurePasswordHere]

Admin created successfully!
Admin ID: 1
Name: System Administrator
Email: admin@college.edu
Role: admin
```

---

### 5. Launch Backend Services

The complete system requires two concurrent backend execution processes:

#### Process 1: FastAPI Core Server & ML Scheduler
Start the main ASGI server with live reloading enabled:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*On Windows, you can alternatively execute the provided launcher:*
```cmd
run_backend.bat
```

* Swagger UI Documentation: **`http://127.0.0.1:8000/docs`**
* ReDoc Specification: **`http://127.0.0.1:8000/redoc`**

#### Process 2: Asynchronous RAG Ingestion Worker (Redis Queue)
In a separate terminal (with the virtual environment activated), start the background OCR and vectorization worker:

```bash
python -m app.workers.rag_worker
```
*(The worker automatically uses `SimpleWorker` on Windows and `Worker` on Linux).*

---

## 📁 Repository Directory Structure

```text
AI_Smart_College_System/
├── app/
│   ├── main.py                     # Primary FastAPI application entrypoint & middleware
│   ├── database/
│   │   ├── database.py             # SQLAlchemy engine, SessionLocal, and DB connection
│   │   └── models.py               # Complete 35 SQLAlchemy ORM models definitions
│   ├── routers/                    # 24 Functional API Routers
│   │   ├── auth.py                 # JWT login, registration, and user profiles
│   │   ├── admission.py            # Student admission applications and enrollment
│   │   ├── fee.py                  # Fee structures, invoicing, receipts, and refunds
│   │   ├── library.py              # Book inventory, barcode circulation, fines
│   │   ├── hod.py                  # Departmental governance and faculty metrics
│   │   ├── department.py           # Department CRUD operations
│   │   ├── faculty.py              # Faculty records and assignments
│   │   ├── student.py              # Student directory and record management
│   │   ├── course.py               # Degree courses and curriculum mapping
│   │   ├── subject.py              # Subjects and semester allocations
│   │   ├── faculty_subject.py      # Teaching responsibility allocations
│   │   ├── attendance.py           # Lecture attendance logging and summaries
│   │   ├── marks.py                # Academic marks and examination results
│   │   ├── assignment.py           # Homework submissions and grading
│   │   ├── performance.py          # Calculated academic transcripts and GPAs
│   │   ├── risk.py                 # Dropout risk classification endpoints
│   │   ├── prediction.py           # ML GPA trajectory and pass/fail predictions
│   │   ├── segmentation.py         # K-Means student cohort clustering
│   │   ├── recommendation.py       # Automated remedial guidance recommendations
│   │   ├── rag_documents.py        # Document uploads, vectorization, and search
│   │   ├── ai_assistant.py         # Autonomous LangChain Gemini assistant & SQL tools
│   │   ├── chat.py                 # Campus chat REST and WebSocket endpoints
│   │   ├── dashboard.py            # Role-tailored metrics and operational KPIs
│   │   └── intelligence.py         # Institutional analytics and predictive summaries
│   ├── schemas/                    # Pydantic validation models
│   │   ├── auth.py
│   │   ├── admission.py
│   │   └── chat.py
│   ├── services/                   # Business logic and external engine connectors
│   │   ├── ai_assistant.py         # LangChain Gemini agent orchestration
│   │   ├── ai_tools.py             # Dynamic role-scoped SQL inspection tools
│   │   ├── chat_manager.py         # Asynchronous WebSocket connection manager
│   │   ├── future_prediction_model.py # GPA regression and trajectory forecasting
│   │   ├── ml_dataset_service.py   # Feature store extraction and normalization
│   │   ├── ml_scheduler.py         # APScheduler background cron orchestrator
│   │   ├── performance_service.py  # GPA, SPI, and CPI tabulators
│   │   ├── prediction_service.py   # Dropout risk classification service
│   │   ├── rag_jobs.py             # Document vectorization job tracker
│   │   ├── rag_queue.py            # Redis Queue connection and job submission
│   │   ├── rag_service.py          # PyMuPDF, Tesseract OCR, and pgvector operations
│   │   ├── recommendation_service.py # Academic improvement roadmap generation
│   │   └── segmentation_service.py # K-Means student clustering algorithms
│   ├── utils/                      # Utilities and security middleware
│   │   ├── auth.py                 # JWT encoding/decoding and RBAC dependency guards
│   │   └── security.py             # Bcrypt password hashing and verification
│   └── workers/                    # Standalone background queue workers
│       ├── rag_worker.py           # Redis Queue (RQ) document processing worker
│       └── rag_scheduler.py        # Worker retry scheduler
├── uploads/                        # Institutional document store for RAG ingestion
├── create_admin.py                 # Initial super-admin provisioning script
├── requirements.txt                # Production Python dependencies manifest
├── run_backend.bat                 # Windows execution batch launcher
├── run_backend.ps1                 # Windows PowerShell execution launcher
├── .env.example                    # Template environment configuration
└── README.md                       # Comprehensive Backend Architecture Documentation
```

---

## 🚢 Production Deployment & Scaling Guidelines

```mermaid
flowchart TD
    INTERNET["Public Internet Traffic"] --> NGINX["NGINX Reverse Proxy / SSL Termination"]
    
    subgraph AppCluster["Backend Application Cluster"]
        NGINX -->|HTTP / REST| GUNICORN["Gunicorn Master Process"]
        GUNICORN --> W1["Uvicorn Worker 1"]
        GUNICORN --> W2["Uvicorn Worker 2"]
        GUNICORN --> W3["Uvicorn Worker 3"]
        GUNICORN --> W4["Uvicorn Worker 4"]
        NGINX -->|WebSocket: /chat/ws| GUNICORN
    end

    subgraph DataCluster["Production Data Tier"]
        W1 & W2 & W3 & W4 --> PGBOUNCER["PgBouncer Connection Pooler"]
        PGBOUNCER --> PG_MASTER[("PostgreSQL 16 Primary + pgvector")]
        W1 & W2 & W3 & W4 --> REDIS_PROD[("Redis 7 High-Availability Cluster")]
    end

    subgraph WorkerCluster["Asynchronous Background Workers"]
        REDIS_PROD --> RQ_W1["RQ Document Worker 1 (OCR)"]
        REDIS_PROD --> RQ_W2["RQ Document Worker 2 (OCR)"]
        W1 --> APSCHED["APScheduler (Leader Only)"]
    end
```

### 1. Process Management with Gunicorn + Uvicorn Workers
In production Linux environments, run FastAPI through Gunicorn using Uvicorn worker classes:
```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/ai_college/access.log \
    --error-logfile /var/log/ai_college/error.log \
    --daemon
```

### 2. PostgreSQL Connection Pooling (`PgBouncer`)
Because FastAPI processes handle hundreds of concurrent async requests, direct connection saturation can occur on PostgreSQL. Deploy **PgBouncer** in transaction pooling mode between FastAPI and PostgreSQL:
* Set `pool_mode = transaction`.
* Set `max_client_conn = 1000`.
* Set `default_pool_size = 25`.

### 3. Redis Persistence & Memory Management
* Configure Redis with `maxmemory-policy allkeys-lru` to allow ephemeral semantic search caches to evict smoothly while safeguarding RQ job queues.
* Enable AOF (Append Only File) persistence (`appendonly yes`) to ensure RAG job queues survive container or server restarts.

### 4. Background Worker Scaling
* Deploy multiple instances of `app/workers/rag_worker.py` across worker nodes to scale document OCR and vectorization capacity during high-volume document ingestion.
* Isolate APScheduler to a single leader worker to prevent duplicate nightly ML recalibration executions.

---

## 📄 License & Intellectual Property

This software and its associated codebase, database schemas, machine learning models, and architecture documents are proprietary. Unauthorized copying, distribution, modification, or commercial exploitation is strictly prohibited without explicit written consent from the institutional governing body.

---

<p align="center">
  <b>AI Smart College Management & Student Intelligence System</b><br>
  <i>Built for Higher Education Excellence</i>
</p>

