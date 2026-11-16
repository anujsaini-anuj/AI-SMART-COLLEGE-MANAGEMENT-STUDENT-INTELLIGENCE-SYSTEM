# 🎓 AI Smart College Management & Student Intelligence System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6.3-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4.10-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4.14-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangChain](https://img.shields.io/badge/LangChain-Google_Gemini-1C3C3C.svg?style=flat&logo=langchain&logoColor=white)](https://langchain.com/)
[![Redis](https://img.shields.io/badge/Redis-RQ_Worker-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML_Pipeline-F7931E.svg?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

An enterprise-grade, full-stack Academic ERP and Artificial Intelligence platform designed to modernize higher-education institutions. It combines comprehensive institutional resource planning, machine-learning-driven student risk analytics, multimodal document RAG (Retrieval-Augmented Generation) with Google Gemini, and a high-performance real-time WebSocket campus messaging engine.

---

## 📑 Table of Contents

- [Key Highlights & Capabilities](#-key-highlights--capabilities)
- [System Architecture](#-system-architecture)
- [Role-Based Access Control (RBAC) & Portals](#-role-based-access-control-rbac--portals)
- [Core Functional Modules](#-core-functional-modules)
  - [1. Real-Time WebSocket Campus Chat](#1-real-time-websocket-campus-chat)
  - [2. AI Copilot & Multimodal RAG Engine](#2-ai-copilot--multimodal-rag-engine)
  - [3. Predictive ML & Early-Warning Radar](#3-predictive-ml--early-warning-radar)
  - [4. Academics, Attendance & Gradebook](#4-academics-attendance--gradebook)
  - [5. Online Admissions Pipeline](#5-online-admissions-pipeline)
  - [6. Financial Accounting & Fees Ledger](#6-financial-accounting--fees-ledger)
  - [7. Digital Library & Circulation Desk](#7-digital-library--circulation-desk)
- [Backend Routers & API Directory](#-backend-routers--api-directory)
- [Database Architecture & Entities](#-database-architecture--entities)
- [Getting Started & Installation](#-getting-started--installation)
  - [Prerequisites](#prerequisites)
  - [Environment Variables (.env)](#environment-variables-env)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Creating the First Admin](#creating-the-first-admin)
- [One-Click Startup Scripts](#-one-click-startup-scripts)
- [WebSocket Protocol Specification](#-websocket-protocol-specification)
- [License & Acknowledgments](#-license--acknowledgments)

---

## 🌟 Key Highlights & Capabilities

- **7 Dedicated Institutional Portals**: Custom workspaces for Admin, HOD, Faculty, Student, Admission Officer, Accountant, and Librarian.
- **Multimodal AI RAG Engine**: Ingests college regulations, policies, and documents (`PDF`, `DOCX`, scanned images with Tesseract OCR), embeds them into `pgvector`, and answers queries using Google Gemini with dynamic SQL tools.
- **Real-Time Campus Messenger**: WebSocket-driven instant messaging supporting direct chats, departmental group chats, academic hierarchy permissions, message editing, WhatsApp-style soft deletion ("Delete for Me" and "Delete for Everyone"), typing indicators, and presence receipts.
- **Student Intelligence & Dropout Risk Detection**: scikit-learn models compute early-warning risk scores and forecast GPA trajectories to generate actionable interventions.
- **Modern Responsive UI**: Built with React 18, TypeScript, Tailwind CSS, Lucide Icons, and Recharts with smooth animations and comprehensive dark/light institutional aesthetics.
- **Automated Asynchronous Infrastructure**: Redis task queues (`RQ`) for background document processing and `APScheduler` for periodic ML inference and training jobs.

---

## 🏛️ System Architecture

```text
                                     +-------------------------------------------+
                                     |    React 18 + Vite + TypeScript Client   |
                                     | (Tailwind CSS, Recharts, Lucide, Axios)   |
                                     +---------------------+---------------------+
                                                           |
                                      HTTP REST / JWT Auth | WebSocket Protocol
                                                           v
+--------------------------------------------------------------------------------------------------------+
|                                        FastAPI Application Server                                      |
|                                                                                                        |
|  [24 Specialized Routers: Auth, Academics, Chat, HOD, Faculty, Admissions, Fees, Library, AI, etc.]   |
|                                                                                                        |
|  +--------------------+   +-----------------------+   +-------------------+   +---------------------+  |
|  |  WebSocket Manager |   |   LangChain / Gemini  |   |  ML Inference &   |   |   APScheduler &     |  |
|  |  (Rooms & Events)  |   |  RAG + DB Tool Agent  |   |  Scikit Pipelines |   |   Security Guard    |  |
|  +--------------------+   +-----------------------+   +-------------------+   +---------------------+  |
+-------------------+-----------------------+--------------------+-----------------------+---------------+
                    |                       |                    |                       |
                    v                       v                    v                       v
      +---------------------------+   +---------------+   +---------------+   +--------------------+
      |  PostgreSQL Database      |   | Google Gemini |   | Redis Queue   |   | Tesseract OCR Engine
      |  - Relational Tables      |   | (LLM API &    |   | (Async Worker |   | (Image & Scanned
      |  - pgvector Embeddings    |   |  Embeddings)  |   |  Doc Indexer) |   |  PDF Text Parsing) |
      +---------------------------+   +---------------+   +---------------+   +--------------------+
```

### Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Axios, Web Audio API |
| **Backend Framework** | FastAPI, Uvicorn, Starlette, Pydantic v2, Python-Jose (JWT), Passlib (Bcrypt) |
| **Database & Vector** | PostgreSQL 14+, SQLAlchemy 2.0 ORM, `pgvector` extension |
| **AI / LLM & RAG** | Google Gemini (2.0 / Flash / Pro), LangChain, PyMuPDF (fitz), python-docx, PyTesseract |
| **Machine Learning** | scikit-learn, Pandas, NumPy, SciPy, Joblib, APScheduler |
| **Async Jobs & Queue**| Redis, RQ (Redis Queue), Background Worker Processes |
| **Real-Time Engine** | Native FastAPI WebSockets, Custom In-Memory & Distributed Pub/Sub Manager |

---

## 🛡️ Role-Based Access Control (RBAC) & Portals

The application implements granular, role-based route guards and permission checks across 7 institutional personas:

```
+------------------------------------------------------------------------------------------+
| Persona      | Dashboard & Workspace Routes                 | Functional Scope           |
+------------------------------------------------------------------------------------------+
| 👑 ADMIN     | /admin/dashboard                             | Institutional Governance,  |
|              | /admin/academics                             | Departments, Courses,      |
|              | /admin/directory                             | Subjects, Faculty/Student  |
|              | /admin/finance-library                       | Onboarding, Fee/Library    |
|              | /admin/ai-control                            | Control, ML Pipelines,     |
|              |                                              | RAG Document Indexing      |
+------------------------------------------------------------------------------------------+
| 🎓 HOD       | /hod/dashboard                               | Department Oversight,      |
|              | /hod/workload                                | Faculty Allocations,       |
|              | /hod/academic-audit                          | Student Attendance Audit,  |
|              | /hod/ai-analytics                            | Early Warning Radar,       |
|              |                                              | Academic Intervention Plans|
+------------------------------------------------------------------------------------------+
| 👨‍🏫 FACULTY   | /faculty/dashboard                           | Subject Management, Smart  |
|              | /faculty/attendance                          | Attendance Register,       |
|              | /faculty/assignments                         | Assignment Grading,        |
|              | /faculty/marks                               | Spreadsheet Gradebook,     |
|              | /faculty/ai-insights                         | Class AI Analytics         |
+------------------------------------------------------------------------------------------+
| 📚 STUDENT   | /student/dashboard                           | Scholar Dashboard, Course  |
|              | /student/academics                           | Attendance Gauge, Marks,   |
|              | /student/fees-library                        | Assignments, Fee Dues &    |
|              | /student/study-coach                         | Receipts, Library Books,   |
|              |                                              | AI Study Recommendations   |
+------------------------------------------------------------------------------------------+
| 📝 ADMISSION | /admission/dashboard                         | Applicant Review Pipeline, |
|    OFFICER   |                                              | Document Verification,     |
|              |                                              | Approval / Rejection Desk  |
+------------------------------------------------------------------------------------------+
| 💳 ACCOUNTANT| /accountant/dashboard                        | Fee Structures Setup,      |
|              |                                              | Student Fee Ledgers,       |
|              |                                              | Payment Collection, Fines  |
+------------------------------------------------------------------------------------------+
| 📖 LIBRARIAN | /librarian/dashboard                         | Book Cataloging, Barcodes, |
|              |                                              | Circulation Desk (Issues & |
|              |                                              | Returns), Overdue Tracking |
+------------------------------------------------------------------------------------------+
| 🌐 ALL USERS | /chat                                        | Real-time Instant Campus   |
|              | /ai-assistant                                | Messenger, Dual-Mode AI    |
|              |                                              | Copilot (Drawer & Page)    |
+------------------------------------------------------------------------------------------+
```

---

## 🚀 Core Functional Modules

### 1. Real-Time WebSocket Campus Chat
* **Academic Policy Verification (`is_chat_allowed`)**:
  * Students can only initiate chats with classmates in their same department, course, batch, and semester, or faculty assigned to teach their registered subjects.
  * Faculty members can communicate with fellow department colleagues and students enrolled in their classes.
  * HODs and Administrators have institutional oversight communication capabilities.
* **Dual Deletion Engine**:
  * **"Delete for Me"**: Removes the message exclusively from the user's view (persisted in `ChatMessageDeletion`) while leaving it intact for others.
  * **"Delete for Everyone"**: Available to the message author; converts the message into an italicized *"This message was deleted"* placeholder for all conversation participants.
* **Inline Message Editing**: Allows senders to modify messages in place; broadcasts updates and displays an `(edited)` indicator.
* **Delivery & Read Acknowledgments**: Real-time single check (Sent), double check (Delivered), and double cyan check (Read) receipts.
* **Presence & Typing Status**: Broadcasts online/offline activity rings and typing bubble indicators.

### 2. AI Copilot & Multimodal RAG Engine
* **Multimodal Document Processing**: Uploads PDFs, Word documents (`DOCX`), and image scans. Utilizes Tesseract OCR for text extraction from images.
* **Vector Semantic Retrieval**: Chunks documents using PyMuPDF, generates embeddings, and indexes them in PostgreSQL with `pgvector` cosine similarity search.
* **Hybrid Tool Execution**: When queried, the LangChain agent intelligently combines vector document context (e.g., college handbook, examination rules) with live SQL database tools (e.g., student attendance records, fee status).
* **Dual UI Modes**: Full-page `/ai-assistant` interface and a floating, slide-over Copilot drawer available from any portal.

### 3. Predictive ML & Early-Warning Radar
* **Dropout & Performance Risk Models**: Ingests attendance patterns, assignment scores, and mid-term marks to flag at-risk students before final examinations.
* **K-Means Student Segmentation**: Clusters students into academic performance tiers (*High Performers, Average, Struggling, At-Risk*).
* **Automated Scheduler**: Background `APScheduler` jobs re-train models and update risk scores periodically.

### 4. Academics, Attendance & Gradebook
* **Smart Attendance**: Bulk "Mark All Present" toggle, absent toggles, and automatic `< 75%` eligibility warnings.
* **Spreadsheet Gradebook**: Dynamic mark entry validating obtained marks against maximum limits.
* **Curriculum Workload Allocation**: HODs assign faculty members to specific subjects, batches, and lecture sections.

### 5. Online Admissions Pipeline
* **Public 3-Step Application Form (`/admissions/apply`)**: Personal information, academic history, course preference, and document uploads.
* **Officer Review Desk**: Filter by status (*Submitted, Under Review, Approved, Rejected*), preview applicant credentials, and generate admission offers.

### 6. Financial Accounting & Fees Ledger
* **Fee Structure Management**: Define annual/semester fee rules by course and academic year.
* **Student Ledgers**: Real-time payment tracking, partial payment handling, automated late fee calculation, and printable receipt generation.

### 7. Digital Library & Circulation Desk
* **Catalog & Accessioning**: Search books by ISBN, title, category, and author. Track individual book copy barcodes and condition states.
* **Circulation Desk**: Issue and return book copies, view active borrow histories, and calculate overdue return fines.

---

## 📡 Backend Routers & API Directory

The FastAPI backend exposes 24 structured routers under intuitive prefixes:

| Router Module | Path Prefix | Key Functionality |
| :--- | :--- | :--- |
| `auth.py` | `/auth` | JWT Authentication, password hashing, login, token refresh, and profile |
| `chat.py` | `/chat` | WebSocket hub (`/ws/{conv_id}`), direct/group chat creation, contacts, history |
| `dashboard.py` | `/dashboard` | Persona-specific aggregate metrics for Admin, Faculty, HOD, Student, etc. |
| `hod.py` | `/hod` | Department faculty rosters, workload, attendance audit, and student reports |
| `admission.py` | `/admissions` | Online application submission, applicant queue, and approval workflows |
| `fee.py` | `/fees` | Fee structures, student ledgers, fee payments, and financial summaries |
| `library.py` | `/library` | Book cataloging, copy tracking, issue/return circulation, and overdue fines |
| `department.py`| `/departments` | Department CRUD, HOD assignments, and capacity stats |
| `course.py` | `/courses` | Degree programs, semester counts, and course catalogs |
| `subject.py` | `/subjects` | Subject codes, credits, semesters, and curriculum mapping |
| `faculty.py` | `/faculties` | Faculty directory, designations, and profiles |
| `faculty_subject.py`| `/faculty-subjects`| Instructor-to-subject assignment matrix |
| `student.py` | `/students` | Student enrollment, department assignments, and biodata |
| `attendance.py`| `/attendance` | Daily attendance logging, subject attendance records, and student percentages |
| `marks.py` | `/marks` | Exam records, internal marks, gradebook entries, and subject scorecards |
| `assignment.py`| `/assignments` | Coursework assignments, submission tracking, and grading |
| `performance.py`| `/performance` | Computed academic performance scores and GPA aggregations |
| `risk.py` | `/risk` | Student risk calculations and early warning classifications |
| `prediction.py`| `/prediction` | ML model endpoints for student outcomes and dropout forecasts |
| `segmentation.py`| `/segmentation` | K-Means student clustering and cohort analysis |
| `recommendation.py`| `/recommendation`| AI-generated remedial guidance and intervention tips |
| `rag_documents.py`| `/rag-documents`| PDF/DOCX document upload, OCR processing, and vector ingestion |
| `ai_assistant.py`| `/ai-assistant` | Interactive conversational AI endpoint with RAG and database query tools |
| `intelligence.py`| `/intelligence` | Comprehensive college-wide intelligence analytics and insight summaries |

---

## 🗄️ Database Architecture & Entities

PostgreSQL stores both structured business entities and high-dimensional vector embeddings:

```text
[User] 1---1 [Student / Faculty / HOD]
  |
  +--- [Department] 1---N [Course] 1---N [Subject]
  |                                        |
  +--- [Attendance] <----------------------+
  +--- [Marks] <---------------------------+
  +--- [Assignment] <----------------------+
  +--- [Performance] & [StudentRisk]
  |
  +--- [AdmissionApplication]
  +--- [FeeStructure] 1---N [StudentFee] 1---N [FeePayment]
  +--- [Book] 1---N [BookCopy] 1---N [BookIssue]
  |
  +--- [ChatConversation] 1---N [ChatParticipant]
  |         |
  |         +--- 1---N [ChatMessage] 1---N [ChatMessageReceipt]
  |                           |
  |                           +--- 1---N [ChatMessageDeletion]
  |
  +--- [DocumentChunk] (stores pgvector embeddings)
```

---

## 💻 Getting Started & Installation

### Prerequisites

Ensure the following runtimes and services are installed on your machine:
- **Python**: Version `3.10` or higher
- **Node.js**: Version `18.x` or higher (a portable Node `v20.18.0` is also included in `node_bin/` for Windows)
- **PostgreSQL**: Version `14+` with the `pgvector` extension enabled
- **Redis**: Local or cloud Redis instance for background queues
- **Tesseract OCR**: (Optional, for image text extraction) `C:\Program Files\Tesseract-OCR\tesseract.exe`

---

### Environment Variables (.env)

Create or update the `.env` file in the project root directory:

```env
# Database Connection (PostgreSQL + pgvector)
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ai_college_db

# Google Gemini API Key (for RAG & AI Copilot)
GEMINI_API_KEY=your_gemini_api_key_here

# Redis Queue (for async document processing)
REDIS_URL=redis://localhost:6379/0

# JWT Security
SECRET_KEY=your_generated_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# OCR Configuration
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_LANGUAGE=eng
RAG_VISION_ENABLED=true
```

---

### Backend Setup

1. **Activate Python Virtual Environment**:
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux / macOS
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Enable `pgvector` in PostgreSQL**:
   Open PostgreSQL for your target database:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. **Run Database Migrations & Tables Initialization**:
   Tables are automatically created on startup by SQLAlchemy `Base.metadata.create_all(bind=engine)`.

5. **Start the FastAPI Backend**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   *Swagger API Documentation will be available at:* `http://127.0.0.1:8000/docs`

---

### Creating the First Admin

Run the interactive admin creation script:
```bash
python create_admin.py
```
Follow the prompts to enter:
- Admin Name
- Admin Email
- Admin Password

You can now use these credentials to log in at `http://localhost:5173/login`.

---

### Frontend Setup

1. **Navigate to Frontend Directory**:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Start Vite Development Server**:
   ```bash
   npm run dev
   ```
   *The application will launch on:* `http://localhost:5173`

4. **Production Build**:
   ```bash
   npm run build
   ```
   *Compiles TypeScript and bundles assets into `frontend/dist/`.*

---

## ⚡ One-Click Startup Scripts (Windows)

For streamlined development on Windows, pre-configured launcher scripts are provided:

| Script | Purpose | Command / Target |
| :--- | :--- | :--- |
| `run_backend.bat` | Activates Python venv and launches Uvicorn | `http://127.0.0.1:8000` |
| `run_frontend.bat` | Uses portable Node runtime and launches Vite dev server | `http://localhost:5173` |
| `build_frontend.bat`| Executes `tsc && vite build` for production verification | Outputs to `frontend/dist/` |

---

## 💬 WebSocket Protocol Specification

The real-time campus chat engine communicates over `ws://127.0.0.1:8000/chat/ws/{conversation_id}`.

### Client to Server Messages

```json
// 1. Initial Authentication Handshake
{ "type": "auth", "token": "JWT_ACCESS_TOKEN" }

// 2. Send Message
{ "type": "send", "content": "Hello team, tomorrow's lecture is at 10 AM." }

// 3. Edit Message
{ "type": "edit", "message_id": 42, "content": "Updated announcement text." }

// 4. Delete Message (Delete for Me)
{ "type": "delete", "message_id": 42, "delete_type": "me" }

// 5. Delete Message (Delete for Everyone)
{ "type": "delete", "message_id": 42, "delete_type": "everyone" }

// 6. Typing Indicator
{ "type": "typing", "is_typing": true }

// 7. Delivery / Read Receipts
{ "type": "delivered", "message_id": 42 }
{ "type": "read", "message_id": 42 }

// 8. Heartbeat
{ "type": "ping" }
```

### Server to Client Messages

```json
// Connected Acknowledgement
{ "type": "connected", "user_id": 10 }

// Incoming Message
{ "type": "message", "message_id": 42, "conversation_id": 5, "sender_id": 10, "sender_name": "Dr. Sharma", "content": "...", "created_at": "..." }

// Message Edited Broadcast
{ "type": "message_edited", "message_id": 42, "conversation_id": 5, "sender_id": 10, "content": "Updated text", "edited_at": "..." }

// Message Deleted for Me (Targeted to User)
{ "type": "message_deleted_for_me", "message_id": 42, "conversation_id": 5, "deleted_by": 10 }

// Message Deleted for Everyone (Broadcast)
{ "type": "message_deleted", "message_id": 42, "conversation_id": 5, "deleted_by": 10, "content": "This message was deleted", "is_deleted": true }

// Presence Status
{ "type": "presence", "user_id": 12, "status": "online" }
```

---

## 📄 License & Acknowledgments

- **Developed for**: AI Smart College Systems & Higher Education Institutions.
- **AI Engine**: Powered by Google Gemini and LangChain.
- **Vector Search**: Enabled by PostgreSQL & `pgvector`.
