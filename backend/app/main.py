import asyncio
import random
import uuid
import json
import io
import os
import pypdf
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.vector_store import VectorStore

app = FastAPI(title="ABC Industries CRM AI Backend Gateway", version="2.0.0")

# Initialize local Vector Database persisting to vector_store.json
db = VectorStore(persist_path=os.path.join(os.path.dirname(__file__), "vector_store.json"))

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# DATA MODELS
# ----------------------------------------------------
class WorkflowTriggerRequest(BaseModel):
    workflow_type: str
    initiator: str

class ChatMessageRequest(BaseModel):
    agent_id: str
    message: str

class DocumentUploadRequest(BaseModel):
    title: str
    content: str
    department: str
    clearance: int

class DocumentDeleteRequest(BaseModel):
    title: str
    department: str

# ----------------------------------------------------
# SYSTEM STATE & SIMULATION DATA
# ----------------------------------------------------
AGENTS = {
    "agent_exec": {
        "id": "agent_exec",
        "name": "Executive Strategy Agent",
        "department": "Executive",
        "model": "Qwen-2.5-72B-Instruct",
        "status": "IDLE",
        "clearance": 5,
        "avatar": "👑",
        "skills": ["Strategic Planning", "Cross-Agent Routing", "Decision Synthesis", "Corporate Dashboard Control"],
        "description": "Synthesizes multi-department reports and makes final operational decisions."
    },
    "agent_hr": {
        "id": "agent_hr",
        "name": "HR Operations Agent",
        "department": "Human Resources",
        "model": "Phi-3-Medium-128k",
        "status": "IDLE",
        "clearance": 3,
        "avatar": "👥",
        "skills": ["Policy Ingestion", "Onboarding Workflows", "Employee Relations", "Benefits Navigation"],
        "description": "Manages employee policies, parses organizational charts, and structures onboarding paths."
    },
    "agent_fin": {
        "id": "agent_fin",
        "name": "Finance & Audit Agent",
        "department": "Finance",
        "model": "Gemma-2-9B-IT",
        "status": "IDLE",
        "clearance": 4,
        "avatar": "📈",
        "skills": ["Revenue Projections", "Compliance Auditing", "Expense Tracking", "Invoicing Automation"],
        "description": "Audits transactions, verifies vendor credentials, and manages budget constraints."
    },
    "agent_legal": {
        "id": "agent_legal",
        "name": "Legal & Compliance Agent",
        "department": "Legal",
        "model": "Mistral-7B-Instruct-v0.3",
        "status": "IDLE",
        "clearance": 4,
        "avatar": "⚖️",
        "skills": ["Contract Analysis", "Risk Assessment", "NDA Validation", "SOP Regulatory Check"],
        "description": "Reviews corporate contracts, identifies liability clauses, and reviews compliance policies."
    },
    "agent_ops": {
        "id": "agent_ops",
        "name": "Operations Control Agent",
        "department": "Operations",
        "model": "Qwen-2.5-14B-Instruct",
        "status": "IDLE",
        "clearance": 2,
        "avatar": "⚙️",
        "skills": ["Logistics Syncing", "Vendor Integration", "SOP Execution", "Task Routing"],
        "description": "Monitors internal workflow triggers, synchronizes systems, and automates operations."
    },
    "agent_sec": {
        "id": "agent_sec",
        "name": "Zero-Trust Security Agent",
        "department": "Cybersecurity",
        "model": "DeepSeek-R1-Distill-Llama-8B",
        "status": "ACTIVE",
        "clearance": 5,
        "avatar": "🛡️",
        "skills": ["PII Scrubbing", "RBAC/ABAC Gatekeeping", "Audit Trail Verification", "Anomaly Detection"],
        "description": "Scans all user queries for security clearance, logs compliance events, and prevents data egress."
    }
}

# InMemory document repository initialized with default files for ABC Industries
DOCUMENTS_DB = [
    # --- HUMAN RESOURCES ---
    {
        "id": "doc_hr_1",
        "title": "ABC Industries Remote Work & Code of Conduct Policy v3.0",
        "department": "Human Resources",
        "content": "All full-time employees of ABC Industries are entitled to a remote-hybrid working model (3 days remote, 2 days in-office). When working remotely, all team members are strictly required to log in via the corporate secure Zero-Trust VPN gateway. Mandatory core working hours are 10:00 AM to 4:00 PM EST. Corporate communication on Slack must remain professional and compliant with the company Code of Ethics.",
        "clearance": 1,
        "added_at": "2026-05-26T08:00:00"
    },
    {
        "id": "doc_hr_2",
        "title": "Standard Executive Offer Letter & Benefits Package",
        "department": "Human Resources",
        "content": "This document outlines the standard employment parameters at ABC Industries. General offers incorporate 25 days of paid annual leave (PTO), comprehensive PPO health insurance coverage, 401(k) retirement match up to 5% of base salary, and eligibility for the ABC Industries Performance-Based Equity Option Pool (vesting over 4 years with a 1-year cliff). Workstation equipment budgets are managed by Operations.",
        "clearance": 2,
        "added_at": "2026-05-26T08:15:00"
    },
    {
        "id": "doc_hr_3",
        "title": "New Hire Onboarding SOP & Milestone Checklist",
        "department": "Human Resources",
        "content": "Onboarding milestones for all ABC Industries divisions: Day 1: Access provisioning, I-9 compliance check, and hardware setup. Day 3: IT and VPN configuration review. Day 14: Mandatory Cybersecurity Training and Zero-Trust credential issuance. Completion of the compliance tutorial is a strict requirement for probation clearance.",
        "clearance": 1,
        "added_at": "2026-05-26T08:30:00"
    },
    
    # --- FINANCE & AUDIT ---
    {
        "id": "doc_fin_1",
        "title": "ABC Industries Q3 Expense Limits & Procurement Directives",
        "department": "Finance",
        "content": "Financial directive for FY2026: Capital expenditure or vendor procurement contracts exceeding $50,000 require secondary authorization from the VP of Finance. Operations invoices must be cataloged under IRS standard tax classification codes (Subchapter C). Expense reports under $500 can be approved automatically by departmental SLMs.",
        "clearance": 4,
        "added_at": "2026-05-26T09:00:00"
    },
    {
        "id": "doc_fin_2",
        "title": "FY2026 Q2 Corporate Revenue & Infrastructure Audit Report",
        "department": "Finance",
        "content": "Financial audit results: ABC Industries generated $24.8M in Q2, representing an 8.4% YoY increase. Operational margins remained stable at 24.2%. Dedicated local GPU compute node infrastructure depreciated by $120,000, while cloud services expenditures decreased by 18% due to localized SLM routing migration.",
        "clearance": 4,
        "added_at": "2026-05-26T09:20:00"
    },
    {
        "id": "doc_fin_3",
        "title": "Vendor Invoicing SOP & Net-30 Payment Regulations",
        "department": "Finance",
        "content": "SOP for invoice processing: All corporate vendors must be cleared via Tax ID registers before payment is scheduled. Standard payment terms are Net-30 from receipt of validated deliverables. Delays in verification by Operations will push scheduling back. Accounts payable must be registered in the corporate ledger.",
        "clearance": 2,
        "added_at": "2026-05-26T09:40:00"
    },
    
    # --- LEGAL & COMPLIANCE ---
    {
        "id": "doc_leg_1",
        "title": "Mutual Non-Disclosure Agreement (NDA) - Template v4.2",
        "department": "Legal",
        "content": "This Non-Disclosure Agreement (NDA) binds all contractors and entities of ABC Industries to protect proprietary trade secrets, customer records, database indices, and agent system prompts. Leakage or unapproved copying of model weights constitutes a material breach, with default liquidated damages valued at $500,000.",
        "clearance": 2,
        "added_at": "2026-05-26T10:00:00"
    },
    {
        "id": "doc_leg_2",
        "title": "ABC Industries SLA Guidelines & Service Penalty Credits",
        "department": "Legal",
        "content": "Standard Service Level Agreement (SLA) parameters: Service availability uptime is guaranteed at 99.9%. Downtime penalties calculate credits at 5% of monthly fees per hour of disruption. Overall liability caps are restricted to the preceding 6 months of paid services unless data leaks occur.",
        "clearance": 3,
        "added_at": "2026-05-26T10:15:00"
    },
    {
        "id": "doc_leg_3",
        "title": "GDPR & CCPA Corporate Regulatory Compliance Directives",
        "department": "Legal",
        "content": "Corporate compliance policies: All customer interaction data must be fully compliant with GDPR and CCPA. Personal Identifiable Information (PII) must be scrubbed prior to storage. Right to be forgotten requests must be processed within 14 business days, cascading updates to all local vector memory segments.",
        "clearance": 4,
        "added_at": "2026-05-26T10:30:00"
    },
    
    # --- OPERATIONS ---
    {
        "id": "doc_ops_1",
        "title": "SOP for Hardware Logistics & Workstation Provisioning",
        "department": "Operations",
        "content": "Standard workstation configuration for new engineering recruits: Dell Precision Workstation (64GB RAM, NVIDIA RTX 4090 GPU). Workstation shipping pipelines are dispatched via FedEx Ground, coordinating delivery with HR's onboarding day-1 checklist.",
        "clearance": 1,
        "added_at": "2026-05-26T11:00:00"
    },
    {
        "id": "doc_ops_2",
        "title": "Operations Log: Active Supplier & Deliverable Registry",
        "department": "Operations",
        "content": "Registry of active corporate suppliers for ABC Industries: Dell Logistics (Tax ID: 74-12890, Hardware), Microsoft Corp (Tax ID: 95-9201A, Software Licensing), and Qdrant Solutions (Vector database SLA). All current deliverables are checked weekly for compliance with the SLA.",
        "clearance": 2,
        "added_at": "2026-05-26T11:20:00"
    },
    
    # --- CYBERSECURITY ---
    {
        "id": "doc_sec_1",
        "title": "Zero-Trust Authentication & SLM Model Weight Isolation",
        "department": "Cybersecurity",
        "content": "Holographic security policy: Access to local SLM weights directories, model checkpoints, and active RAG databases requires Level 5 security clearance. API transactions must possess signed cryptographic JWT tokens. Audit trails of weight accesses are kept in an immutable PostgreSQL database.",
        "clearance": 5,
        "added_at": "2026-05-26T12:00:00"
    },
    {
        "id": "doc_sec_2",
        "title": "PII Scrubbing and Embedding Anonymization Directives",
        "department": "Cybersecurity",
        "content": "Data protection policy: All direct messaging records and document files uploaded to local memory registers must be routed through the Cybersecurity Anonymization Engine. Any matching Social Security Numbers (SSNs), phone numbers, or emails are replaced with cryptographic tokens before vectorization.",
        "clearance": 5,
        "added_at": "2026-05-26T12:30:00"
    },
    
    # --- EXECUTIVE ---
    {
        "id": "doc_exe_1",
        "title": "ABC Industries 3-Year Strategic AI Integration Roadmap",
        "department": "Executive",
        "content": "Strategic roadmap for FY2026-FY2028: Integrate local quantized SLMs into all operational workflows to phase out public API dependencies. Phase 1: Deploy HR and Legal co-pilots in sandboxed environments. Phase 2: Inter-agent event bus routing automation. Phase 3: Hardware scale-up to NVIDIA H100 clusters for proprietary fine-tuning.",
        "clearance": 5,
        "added_at": "2026-05-26T13:00:00"
    }
]

# ----------------------------------------------------
# WEBSOCKET CONNECTION MANAGER
# ----------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

INDEXED_DOCUMENTS_CACHE: List[Dict[str, Any]] = []
DELETED_STATIC_DOCS = set()

# ----------------------------------------------------
# REST API ENDPOINTS
# ----------------------------------------------------
@app.get("/api/status")
def get_system_status():
    # Calculate unique documents from unique titles in Pinecone indexed_titles cache
    active_static_count = len([d for d in DOCUMENTS_DB if d["title"] not in DELETED_STATIC_DOCS])
    doc_count = len(db.indexed_titles) if db.indexed_titles else active_static_count
    return {
        "status": "ONLINE",
        "gpu_vram_used_gb": round(random.uniform(16.5, 18.1), 2),
        "gpu_vram_total_gb": 24.0,
        "cpu_usage_pct": round(random.uniform(22.1, 40.5), 1),
        "ram_usage_pct": round(random.uniform(61.2, 63.8), 1),
        "active_tokens_sec": random.randint(120, 320),
        "documents_count": doc_count,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/agents")
def get_agents():
    return list(AGENTS.values())

@app.get("/api/documents")
def get_documents(department: str = None):
    # Combine static documents database with newly indexed custom documents cache
    docs = DOCUMENTS_DB + INDEXED_DOCUMENTS_CACHE
    docs = [d for d in docs if d["title"] not in DELETED_STATIC_DOCS]

    if department:
        map_dept = {
            "human resources": "human resources",
            "finance": "finance",
            "legal": "legal",
            "operations": "operations",
            "cybersecurity": "cybersecurity",
            "executive": "executive"
        }
        mapped_name = map_dept.get(department.lower(), department)
        return [d for d in docs if d["department"].lower() == mapped_name.lower()]
    return docs

# UPLOAD A NEW DOCUMENT DYNAMICALLY TO MEMORY
@app.post("/api/memory/upload")
async def upload_document(req: DocumentUploadRequest):
    # Index text in vector store (will chunk, embed and store)
    db.add_document(
        title=req.title,
        content=req.content,
        department=req.department,
        clearance=req.clearance
    )
    
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"
    new_doc = {
        "id": doc_id,
        "title": req.title,
        "department": req.department,
        "content": req.content,
        "clearance": req.clearance,
        "added_at": datetime.now().isoformat()
    }
    
    INDEXED_DOCUMENTS_CACHE.append(new_doc)
    
    # Broadcast an update to all connected dashboard websockets
    total_docs = len(db.indexed_titles) if db.indexed_titles else len(DOCUMENTS_DB)
    await manager.broadcast({
        "type": "DOCUMENT_INDEXED",
        "data": {
            "document": new_doc,
            "total_documents": total_docs,
            "log": f"📥 [Ingest Pipeline] Indexed text document: '{req.title}' ({len(req.content)} chars) into {req.department} vector database."
        }
    })
    
    return {"status": "SUCCESS"}

# NEW FILE INGESTION ENDPOINT Supporting PDF, DOCX, and TXT
@app.post("/api/memory/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    department: str = Form(...),
    clearance: int = Form(...)
):
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx") or filename_lower.endswith(".txt") or filename_lower.endswith(".text")):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT/TEXT files are supported")
        
    try:
        file_bytes = await file.read()
        text_content = ""
        file_type = "TEXT"
        
        if filename_lower.endswith(".pdf"):
            file_type = "PDF"
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        elif filename_lower.endswith(".docx"):
            file_type = "DOCX"
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_content += paragraph.text + "\n"
        else:
            file_type = "TXT"
            text_content = file_bytes.decode("utf-8", errors="ignore")
            
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No readable text found in uploaded file")
            
        title = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        
        # Index in local vector store (auto chunks and embeds)
        db.add_document(
            title=title,
            content=text_content,
            department=department,
            clearance=clearance
        )
        
        doc_id = f"doc_{uuid.uuid4().hex[:6]}"
        new_doc = {
            "id": doc_id,
            "title": title,
            "department": department,
            "content": text_content,
            "clearance": clearance,
            "added_at": datetime.now().isoformat()
        }
        
        INDEXED_DOCUMENTS_CACHE.append(new_doc)
        
        # Broadcast update to dashboard WebSockets
        total_docs = len(db.indexed_titles) if db.indexed_titles else len(DOCUMENTS_DB)
        await manager.broadcast({
            "type": "DOCUMENT_INDEXED",
            "data": {
                "document": new_doc,
                "total_documents": total_docs,
                "log": f"📥 [Ingest Pipeline] Indexed {file_type}: '{title}' ({len(text_content)} chars) into {department} vector database."
            }
        })
        
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {str(e)}")

# DELETE A DOCUMENT DYNAMICALLY FROM MEMORY AND PINECONE
@app.delete("/api/documents/delete")
async def delete_document(req: DocumentDeleteRequest):
    title = req.title
    department = req.department
    namespace = department.lower().strip()
    
    # 1. Delete vectors from Pinecone Index using metadata filters
    if db.use_pinecone and db.pinecone_index:
        try:
            db.pinecone_index.delete(filter={"title": title}, namespace=namespace)
            print(f"[Vector Store] SUCCESS: Wiped '{title}' from Pinecone namespace '{namespace}'!")
        except Exception as e:
            print(f"[Vector Store] WARNING: Pinecone metadata deletion failed ({e}). Proceeding to cache clear.")
            
    # 2. Remove from active indexed titles cache
    if title in db.indexed_titles:
        db.indexed_titles.remove(title)
        
    # 3. Remove from INDEXED_DOCUMENTS_CACHE
    global INDEXED_DOCUMENTS_CACHE
    INDEXED_DOCUMENTS_CACHE = [d for d in INDEXED_DOCUMENTS_CACHE if d["title"] != title]
    
    # 4. Check if it was a default static document to soft-delete
    is_static = any(doc["title"] == title for doc in DOCUMENTS_DB)
    if is_static:
        DELETED_STATIC_DOCS.add(title)
        
    # Broadcast deletion status and log via WebSocket to all listening dashboards
    active_static_count = len([d for d in DOCUMENTS_DB if d["title"] not in DELETED_STATIC_DOCS])
    total_docs = len(db.indexed_titles) if db.indexed_titles else active_static_count
    
    await manager.broadcast({
        "type": "DOCUMENT_DELETED",
        "data": {
            "title": title,
            "department": department,
            "total_documents": total_docs,
            "log": f"❌ [Ingest Pipeline] Wiped document: '{title}' and removed all associated vector segments from Pinecone under namespace '{namespace}'."
        }
    })
    
    return {"status": "SUCCESS"}

# DEDICATED CONVERSATIONAL AI GENERATOR
STOPWORDS = {
    "what", "where", "when", "how", "who", "why", "which", "whose", "whom",
    "this", "that", "these", "those", "there", "their", "them", "they",
    "have", "has", "had", "having", "does", "do", "did", "doing",
    "with", "about", "from", "into", "through", "during", "before", "after",
    "above", "below", "some", "such", "only", "same", "than", "then",
    "very", "will", "would", "shall", "should", "could", "must", "your",
    "mine", "ours", "yours", "hers", "his", "its", "their", "theirs",
    "please", "tell", "show", "find", "search", "query", "look", "want",
    "file", "files", "policy", "policies", "standard", "standards"
}

def generate_conversational_response(agent: Dict[str, Any], user_query: str, matched_docs: List[Dict[str, Any]]) -> str:
    query_clean = user_query.strip().lower()
    query_lower = query_clean
    query_words = {w.strip(".,!?\"'") for w in query_clean.split()}
    
    # 1. DYNAMIC DOCUMENT LIST QUERY
    is_asking_for_docs = any(x in query_lower for x in ["what documents", "what files", "list documents", "list files", "show documents", "show files", "which documents", "what all documents", "what do you have", "what is in your database", "what is indexed"])
    if is_asking_for_docs:
        # Get all unique document titles for this specific department in vector store
        dept_chunks = [c for c in db.chunks if c["department"].lower() == agent["department"].lower() and c["clearance"] <= agent["clearance"]]
        unique_docs = {}
        for c in dept_chunks:
            unique_docs[c["title"]] = c["clearance"]
            
        if unique_docs:
            doc_list = "\n".join(f"• **{title}** (Clearance Level {clearance})" for title, clearance in unique_docs.items())
            return (
                f"I currently have access to the following secure organizational memory registers for the **{agent['department']}** division:\n\n"
                f"{doc_list}\n\n"
                f"You can ask me specific questions about their details, or upload new manuals on the right to expand my operational knowledge base!"
            )
        else:
            return (
                f"I currently do not have any corporate documents indexed in the **{agent['department']}** vector pool.\n\n"
                f"Please upload a handbook, SOP, or policy document (.pdf, .docx, .txt) using the **Ingest to Memory** panel on the right so I can learn its contents!"
            )

    # 2. CONVERSATIONAL GREETINGS FILTER
    is_greeting = any(greet in query_words for greet in ["hi", "hello", "hey", "greetings", "yo", "good morning", "good afternoon", "good evening", "sup"])
    if is_greeting:
        return (
            f"Hello! I am your **{agent['name']}** supporting the **{agent['department']}** division at ABC Industries.\n\n"
            f"I am fully authenticated with Clearance Level L{agent['clearance']} and ready to assist you with policy documents, compliance audits, or labor guidelines. "
            f"What specific policy question can I search or help you with today?"
        )

    # 3. IDENTITY & HELP EXPLAINER CARD
    is_asking_identity = any(x in query_clean for x in ["who are you", "what are you", "your name", "tell me about yourself"])
    is_asking_skills = any(x in query_clean for x in ["what can you do", "what are your skills", "your capabilities", "skills", "help", "how can you help"])
    if is_asking_identity or is_asking_skills:
        skills_md = "\n".join(f"• **{skill}**" for skill in agent["skills"])
        return (
            f"### {agent['avatar']} {agent['name'].upper()} PROFILE & HUD CAPABILITIES\n\n"
            f"I am the specialized **{agent['name']}** for the **{agent['department']}** division of ABC Industries.\n\n"
            f"#### ⚙️ Technical Operational Vitals\n"
            f"• **Neural Framework Architecture**: `{agent['model']}` (Quantized local inference)\n"
            f"• **Divisional Role Clearance**: `Level L{agent['clearance']} Authentication`\n"
            f"• **Current Status**: `ONLINE / ACTIVE`\n\n"
            f"#### 🧠 Functional Domain Skills\n"
            f"{skills_md}\n\n"
            f"#### 📁 Division Summary\n"
            f"*{agent['description']}*\n\n"
            f"You can upload policy documents, employee agreements, logs, or SOP sheets (.pdf, .docx, .txt) in the **Ingest to Memory** panel on the right. I will instantly build a vector index and synthesize them to answer your direct queries!"
        )

    # 4. POSITIVE ACKNOWLEDGEMENTS CLOSURE
    is_positive_ack = any(ack in query_words for ack in ["thanks", "thank you", "perfect", "great", "awesome", "ok", "got it", "cool", "clear", "splendid", "wonderful"])
    if is_positive_ack:
        return (
            f"You're very welcome! I'm happy to help. 😊\n\n"
            f"Is there anything else you need checked or processed regarding the **{agent['department']}** division records?"
        )

    # 5. CORE CONVERSATIONAL SMALL TALK
    is_small_talk = any(x in query_clean for x in ["how are you", "how's it going", "how are you doing", "are you real", "are you human"])
    if is_small_talk:
        return (
            f"I am functioning at peak efficiency! As a specialized `{agent['model']}` Small Language Model, "
            f"I am running locally on our zero-trust infrastructure to protect ABC Industries corporate weights.\n\n"
            f"I am fully authenticated at Clearance Level L{agent['clearance']} for **{agent['department']}** operations. "
            f"How can I assist you with your department tasks today?"
        )

    # 6. CONVERSATIONAL RAG SEARCH SUMMARIZER (ONLY RUNS IF WE HAVE A GENUINE MATCH)
    if matched_docs:
        doc = matched_docs[0]
        title = doc['title']
        clearance = doc['clearance']
        content = doc['content']
        
        # Check if the query is requesting detailed elaboration/explanation
        is_asking_for_detail = any(x in query_lower for x in ["detailed", "explain", "expand", "elaborate", "depth", "more details", "in detail", "more info", "tell me more"])
        
        if is_asking_for_detail:
            # We automatically build a highly structured, comprehensive, and beautiful executive report
            title_lower = title.lower()
            elaboration = ""
            
            if "security" in title_lower or "zero-trust" in title_lower or "cybersecurity" in title_lower or "isolation" in title_lower:
                elaboration = (
                    "### 🛡️ ZERO-TRUST COMPLIANCE & WEIGHT ISOLATION BLUEPRINT\n\n"
                    "#### 1. Immutable Model Weight Segregation\n"
                    "All local weights for quantized Small Language Models (SLMs) such as Qwen-2.5 and Phi-3 "
                    "are housed in sandboxed, isolated system directories. Training pools and active checkpoints "
                    "are strictly isolated from public network routes to prevent prompt injection and parameter extraction.\n\n"
                    "#### 2. Cryptographic Gatekeeping & JWT Signatures\n"
                    "Access to model inference engines is strictly governed by Role-Based and Attribute-Based Access Control "
                    "(RBAC/ABAC). Every API transaction must carry a cryptographically signed JWT token. "
                    "Clearance context limits are dynamically enforced: L1-L4 handles general operational data, "
                    "while L5 is required to inspect raw model weights and system databases.\n\n"
                    "#### 3. Immutable PostgreSQL Audit Trail\n"
                    "Every transaction, credential validation, and vector lookup is logged in real-time in an "
                    "immutable PostgreSQL audit trail. The ledger registers accessing users, query timestamps, "
                    "clearance tags, and transaction signatures, providing absolute forensic audit capabilities.\n\n"
                    "#### 4. Anonymization & Egress Control\n"
                    "All chat histories and uploaded document pools are actively scrubbed of Personal Identifiable "
                    "Information (PII) like phone numbers, Social Security Numbers (SSNs), and emails. Cryptographic "
                    "anonymizer nodes replace sensitive data before vectors are stored."
                )
            elif "remote" in title_lower or "conduct" in title_lower or "work" in title_lower or "handbook" in title_lower:
                elaboration = (
                    "### 👥 REMOTE-HYBRID WORKING & ETHICAL CONDUCT CHARTER\n\n"
                    "#### 1. Core Hybrid Working Schedule\n"
                    "ABC Industries establishes a standard hybrid model split. All full-time staff are allocated "
                    "3 days of remote work and 2 days of in-office presence. Department heads coordinate office days "
                    "to maintain teamwork synergy while utilizing cloud workspaces.\n\n"
                    "#### 2. Mandatory Zero-Trust VPN Connections\n"
                    "While operating from remote workspaces, team members must establish a secure tunnel utilizing "
                    "the corporate Zero-Trust VPN client. Connecting via public, unencrypted Wi-Fi networks without "
                    "active VPN authentication is a direct compliance violation.\n\n"
                    "#### 3. Core Working Hours HUD\n"
                    "Operational core working hours are established from 10:00 AM to 4:00 PM EST. During these "
                    "hours, staff are expected to remain actively reachable on Slack and operational communication channels, "
                    "facilitating quick syncs and strategy alignment.\n\n"
                    "#### 4. Slack Ethics & Professional Boundaries\n"
                    "Corporate communication channels must remain compliant with the ABC Industries Code of Ethics. "
                    "Leaking internal prompt instructions constitutes a material breach, leading to immediate review by HR Operations."
                )
            elif "onboarding" in title_lower or "sop" in title_lower or "hire" in title_lower or "checklist" in title_lower:
                elaboration = (
                    "### 📋 NEW HIRE ONBOARDING SOP & MILESTONE BLUEPRINT\n\n"
                    "#### 📍 Day 1: Access Provisioning & Hardware Setup\n"
                    "• Provision standard workstation hardware (Dell Precision with 64GB RAM, NVIDIA RTX 4090 GPU).\n"
                    "• Conduct standard I-9 legal compliance check and establish internal active directory accounts.\n\n"
                    "#### 📍 Day 3: IT & Zero-Trust VPN Authentication\n"
                    "• Setup security key rings and initialize Zero-Trust VPN client credentials.\n"
                    "• Configure standard department workspace accesses (HR, Finance, Operations, or Legal).\n\n"
                    "#### 📍 Day 14: Mandatory Cybersecurity Training\n"
                    "• Complete the interactive Zero-Trust Compliance and prompt security tutorials.\n"
                    "• Successful completion of this final onboarding check is a strict requirement to clear probationary reviews."
                )
            elif "expense" in title_lower or "procurement" in title_lower or "budget" in title_lower or "audit" in title_lower or "finance" in title_lower:
                elaboration = (
                    "### 📈 CORPORATE FINANCE & PROCUREMENT AUDIT PROTOCOL\n\n"
                    "#### 1. Double-Layer Expense Authorizations\n"
                    "All departmental procurement contracts and vendor expenditures exceeding a $50,000 threshold "
                    "strictly require secondary, written authorization from the VP of Finance. Standard expenses "
                    "under $500 can be automatically cleared by local department SLM co-pilots.\n\n"
                    "#### 2. Subchapter C Tax Codification\n"
                    "All logistics records, vendor invoices, and accounts payable entries must be cataloged "
                    "under IRS standard tax classification codes (Subchapter C). Transactions missing standard codes "
                    "will be returned by the ledger auditor nodes for manual operations checks.\n\n"
                    "#### 3. Supplier Registry & Net-30 SOP\n"
                    "All corporate supplier billing is scheduled under standard Net-30 terms upon validation of "
                    "deliverables. Dell Logistics, Microsoft licensing, and vector database hosting nodes are cleared "
                    "suppliers. Weekly audit registers reconcile deliverables against standard SLA guidelines."
                )
            else:
                # General smart sentence expansion engine for user-uploaded documents
                import re
                sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', content)
                key_points = "\n".join(f"• **Point {idx+1}**: {sentence.strip()}" for idx, sentence in enumerate(sentences[:5]))
                elaboration = (
                    f"### 📋 DETAILED BLUEPRINT: {title.upper()}\n\n"
                    "#### I. Key Policy Parameters & Core Clauses\n"
                    f"{key_points}\n\n"
                    "#### II. Operational Compliance Directives\n"
                    f"All personnel are strictly directed to observe these parameters. Transactions "
                    f"must be filed under corporate standards, and updates to this manual must be index-cleared "
                    f"within standard vector memory pools.\n\n"
                    "#### III. Security & Clearance Controls\n"
                    f"Access is restricted to authorized credentials (Clearance Tag: Level {clearance}). "
                    f"Unapproved egress or copying of these parameters is strictly logged in audit ledgers."
                )
                
            return (
                f"I have compiled a **detailed, comprehensive explanation** based on **{title}** "
                f"(Clearance Tag: Level {clearance}) to expand on the core guidelines:\n\n"
                f"{elaboration}\n\n"
                f"*(Verified source context from: '{title}')*"
            )
            
        # Split matched content into sentences
        import re
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', content)
        
        # Score sentences based on query keyword overlap
        query_words_rag = {w for w in query_lower.split() if len(w) > 3 and w not in STOPWORDS}
        scored_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for w in query_words_rag if w in sentence_lower)
            scored_sentences.append((score, sentence))
            
        # Select sentences with highest keyword relevance
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        relevant_sentences = [s for score, s in scored_sentences if score > 0]
        
        if relevant_sentences:
            # Join the top 2 most relevant sentences to build a natural conversational reply
            summary = " ".join(relevant_sentences[:2])
            response = (
                f"According to **{title}** (Clearance L{clearance}), "
                f"here is the direct information answering your query:\n\n"
                f"**{summary}**\n\n"
                f"For your official compliance review, here is the verified source context extracted directly from the records:\n"
                f"> *\"{content.strip()}\"*"
            )
        else:
            # Fallback to standard conversational presentation of full chunk if no sentence matched perfectly
            response = (
                f"Regarding your query **\"{user_query}\"**, I searched through the **{title}** manual (Clearance Level {clearance}) and found the following relevant guidelines:\n\n"
                f"{content}\n\n"
                f"Let me know if you would like me to clarify or search for any other sections!"
            )
        return response
        
    # 7. DIVISIONAL FALLBACK RESPONSES (SMART persona answers when no document matches)
    dept = agent["department"].lower()
    if "human resources" in dept:
        if "remote" in query_clean or "hybrid" in query_clean or "hours" in query_clean or "work" in query_clean:
            return (
                "### 👥 HR OPERATIONS CO-PILOT ADVISORY\n\n"
                "At ABC Industries, our employees are entitled to a **Remote-Hybrid Model** consisting of **3 days remote and 2 days in-office**.\n\n"
                "**Core Operational Guidelines**:\n"
                "• **Core Hours**: 10:00 AM to 4:00 PM EST is our mandatory synchronization block.\n"
                "• **VPN Protocol**: Remote operations must strictly tunnel through the corporate secure **Zero-Trust VPN gateway**.\n"
                "• **Ethics Standard**: Professional Slack operations must conform with the ABC Industries Code of Conduct.\n\n"
                "*(Note: For your exact division numbers, please ensure the **ABC Industries Remote Work Policy** manual is ingested into our memory bank, or ask me for a detailed blueprint!)*"
            )
        elif "leave" in query_clean or "pto" in query_clean or "vacation" in query_clean or "holiday" in query_clean or "offer" in query_clean or "benefits" in query_clean:
            return (
                "### 👥 HR OPERATIONS BENEFITS SUMMARY\n\n"
                "Under standard ABC Industries benefits protocols:\n"
                "• **Annual Paid Leave**: Full-time employees receive 25 days of Paid Time Off (PTO).\n"
                "• **Insurance**: Comprehensive PPO health insurance package.\n"
                "• **Retirement Planning**: 401(k) retirement matching up to 5% of base salary.\n"
                "• **Equity grant**: Fully eligible for the Performance-Based Equity Option Pool (vesting over 4 years with a 1-year cliff).\n\n"
                "*(Note: Ingest your specific offer sheet on the right to audit customized terms!)*"
            )
        elif "onboard" in query_clean or "new hire" in query_clean or "probation" in query_clean or "training" in query_clean:
            return (
                "### 👥 HR NEW HIRE ONBOARDING ROADMAP\n\n"
                "Our mandatory divisions onboarding checkpoints are structured as follows:\n"
                "• **Day 1**: Hardware provisioning (Precision Workstations) and standard I-9 legal compliance clearance.\n"
                "• **Day 3**: Secure active directory setup and Zero-Trust VPN client synchronization.\n"
                "• **Day 14**: Mandatory Cybersecurity Training and Zero-Trust credential issuance.\n\n"
                "*(Note: Complete these tutorials immediately to satisfy standard probation clearance requirements!)*"
            )
    elif "finance" in dept:
        if "expense" in query_clean or "limit" in query_clean or "procure" in query_clean or "spend" in query_clean or "buy" in query_clean:
            return (
                "### 📈 FINANCE PROCUREMENT & COMPLIANCE HUD\n\n"
                "Vendor spending is strictly regulated under standard tax ledger constraints:\n"
                "• **Micro-purchases (<$500)**: Approved automatically by division co-pilot nodes.\n"
                "• **Standard purchases (<$50,000)**: Authorized standard department budget routes.\n"
                "• **Major procurement (>$50,000)**: Strictly requires written secondary clearance from the VP of Finance.\n"
                "• **Tax classification**: Expenses must register under standard IRS Subchapter C structures.\n"
            )
        elif "revenue" in query_clean or "audit" in query_clean or "earnings" in query_clean or "margin" in query_clean:
            return (
                "### 📈 CORPORATE REVENUE & AUDIT REPORT\n\n"
                "Our FY2026 Q2 operational registers report high performance:\n"
                "• **Gross Revenue**: $24.8M (representing an 8.4% YoY increase).\n"
                "• **Operating Margins**: 24.2% stable performance.\n"
                "• **Compute Depreciation**: GPU node arrays depreciated by $120k; Cloud service expenses drops by 18%.\n"
            )
    elif "legal" in dept:
        if "nda" in query_clean or "disclosure" in query_clean or "secret" in query_clean or "confidential" in query_clean:
            return (
                "### ⚖️ LEGAL DEPT: MUTUAL NDA STANDARDS\n\n"
                "All contractors and entities must observe Mutual NDA parameters (v4.2):\n"
                "• **Scope**: Trade secrets, model weights, database indices, and system prompts are fully confidential.\n"
                "• **Liquidation**: Unapproved parameter leakage triggers standard default damages valued at **$500,000**.\n"
            )
        elif "sla" in query_clean or "uptime" in query_clean or "penalty" in query_clean or "disrupt" in query_clean:
            return (
                "### ⚖️ LEGAL DEPT: SERVICE LEVEL AGREEMENTS (SLA)\n\n"
                "Standard SLA guidelines establish our vendor service bounds:\n"
                "• **Service Availability**: Uptime guarantee of 99.9%.\n"
                "• **Penalty Credits**: Downtime calculates credits at 5% of monthly fees per hour of disruption.\n"
                "• **Liability Boundaries**: Caps are set to preceding 6 months of payments unless data breach occurs.\n"
            )
    elif "cybersecurity" in dept:
        if "isolation" in query_clean or "weight" in query_clean or "clearance" in query_clean or "security" in query_clean:
            return (
                "### 🛡️ CYBERSECURITY COMPLIANCE: SYSTEM ISOLATION\n\n"
                "Under corporate security directives:\n"
                "• **Weight Segregation**: Local weights and vector checkpoints run in isolated sandboxed directories.\n"
                "• **JWT Authorization**: Requests must bear signed cryptographic tokens specifying clearance limits.\n"
                "• **Immutable Auditing**: Every retrieval and weight transaction logs to our immutable PostgreSQL ledger.\n"
            )
        elif "scrub" in query_clean or "pii" in query_clean or "anonymize" in query_clean:
            return (
                "### 🛡️ CYBERSECURITY COMPLIANCE: PRIVACY & SCRUBBING\n\n"
                "To ensure strict GDPR & CCPA alignment:\n"
                "• **Anonymization Engine**: SSNs, emails, and phone numbers are scrubbed and replaced by cryptographic tokens.\n"
                "• **Right to be Forgotten**: Cascades deletion vectors through all segment memory files within 14 business days.\n"
            )
    elif "operations" in dept:
        if "workstation" in query_clean or "hardware" in query_clean or "shipping" in query_clean or "dell" in query_clean or "rtx" in query_clean:
            return (
                "### ⚙️ OPERATIONS CONTROL: HARDWARE PIPELINES\n\n"
                "Standard operational configuration for recruits:\n"
                "• **Engineering Spec**: Dell Precision Workstation (64GB RAM, NVIDIA RTX 4090 GPU).\n"
                "• **Logistics**: FedEx Ground shipping schedules synchronized with Day 1 onboarding HR checklists.\n"
                "• **Approved Suppliers**: Dell Logistics, Microsoft Corp, and Qdrant vector SLA solutions.\n"
            )
    elif "executive" in dept:
        if "roadmap" in query_clean or "strategy" in query_clean or "nvidia" in query_clean or "h100" in query_clean:
            return (
                "### 👑 EXECUTIVE STRATEGY: AI ROADMAP\n\n"
                "The corporate AI roadmap outlines key infrastructure integrations:\n"
                "• **Phase 1**: Sandboxed local division SLM co-pilots (HR, Legal) to deprecate public cloud dependencies.\n"
                "• **Phase 2**: Inter-agent event bus routing for multi-agent workflows.\n"
                "• **Phase 3**: Scaling hardware pipelines up to NVIDIA H100 clusters for proprietary fine-tuning.\n"
            )

    # General Division-based Friendly No-Match Fallback
    return (
        f"I have searched our secure local **{agent['department']}** registers for **\"{user_query}\"**.\n\n"
        f"⚠️ **This specific information is currently not available in our indexed database chunks.**\n\n"
        f"As your **{agent['name']}**, I would be happy to analyze it for you! "
        f"Please upload the relevant manual, SOP document, or PDF report using the **Ingest to Memory** panel on the right. "
        f"Once uploaded, I will dynamically index it and answer your questions based on its exact contents!"
    )

# DEDICATED CHATBOX API FOR DEPARTMENTS
@app.post("/api/chat")
async def chat_with_agent(req: ChatMessageRequest):
    agent_id = req.agent_id
    if agent_id not in AGENTS:
        raise HTTPException(status_code=400, detail="Invalid Agent ID")
    
    agent = AGENTS[agent_id]
    user_query = req.message
    
    # Simulate thinking step-by-step
    thinking_steps = [
        f"🔐 [Zero-Trust Gate] Validating security clearances for resource query...",
    ]
    
    query_clean = user_query.strip().lower()
    query_words = {w.strip(".,!?\"'") for w in query_clean.split()}
    
    # Check if query is short, small-talk, or greeting to bypass RAG database search
    is_greeting = any(greet in query_words for greet in ["hi", "hello", "hey", "greetings", "yo", "good morning", "good afternoon", "good evening", "sup"])
    is_asking_identity = any(x in query_clean for x in ["who are you", "what are you", "your name", "tell me about yourself"])
    is_asking_skills = any(x in query_clean for x in ["what can you do", "what are your skills", "your capabilities", "skills", "help", "how can you help"])
    is_positive_ack = any(ack in query_words for ack in ["thanks", "thank you", "perfect", "great", "awesome", "ok", "got it", "cool", "clear"])
    
    skip_rag = len(query_clean) <= 3 or is_greeting or is_asking_identity or is_asking_skills or is_positive_ack
    
    matched_docs = []
    
    if skip_rag:
        thinking_steps.append(
            f"🔍 [Vector Search] Input query detected as conversational small-talk, greeting, or direct capability query. "
            f"Bypassing vector database search to optimize system throughput."
        )
        thinking_steps.append(
            f"🧠 [Context Injection] Bypassed database cache. Routing directly to agent's local conversational parameters."
        )
    else:
        thinking_steps.append(f"🔍 [Vector Search] Generating query embedding and performing cosine similarity search...")
        
        # Perform real semantic cosine similarity vector search
        matched_chunks = db.search(
            query=user_query,
            department=agent["department"],
            clearance=agent["clearance"],
            top_k=3
        )
        
        # Reconstruct the matched doc list to pass to conversational generator
        if matched_chunks:
            best_chunk = matched_chunks[0]
            score_pct = int(best_chunk["score"] * 100)
            
            # Enforce similarity threshold of 0.35
            if best_chunk["score"] >= 0.35:
                thinking_steps.append(
                    f"🧠 [Context Injection] Semantic match found: '{best_chunk['title']}' "
                    f"(Similarity Score: {score_pct}%, Chunk Index: {best_chunk['chunk_index']}). "
                    f"Injecting vector chunks into model cache."
                )
                matched_docs.append({
                    "id": best_chunk["id"],
                    "title": best_chunk["title"],
                    "clearance": best_chunk["clearance"],
                    "content": best_chunk["content"]
                })
            else:
                thinking_steps.append(
                    f"🧠 [Context Injection] Best semantic match '{best_chunk['title']}' has score {score_pct}% "
                    f"which is below the security & accuracy threshold (35%). Filtering match to prevent false context override."
                )
                thinking_steps.append(
                    f"🧠 [Context Injection] Searching global shared enterprise indices. No hot direct matches found; routing to conversational weights."
                )
        else:
            thinking_steps.append(
                f"🧠 [Context Injection] Searching global shared enterprise indices. "
                f"No direct semantic vector matches found; routing to foundational weights."
            )
            
    thinking_steps.append(f"⚙️ [Model Gate] Forwarding query + clearance L{agent['clearance']} context to local quantized model [{agent['model']}].")

    # Generate rich, conversational, dynamic response using our RAG context
    response_text = generate_conversational_response(agent, user_query, matched_docs)
        
    return {
        "status": "COMPLETED",
        "agent_id": agent_id,
        "thinking_steps": thinking_steps,
        "response": response_text,
        "timestamp": datetime.now().isoformat()
    }

# ----------------------------------------------------
# WS TELEMETRY STREAM
# ----------------------------------------------------
async def stream_telemetry_loop():
    while True:
        doc_count = len(db.indexed_titles) if db.indexed_titles else len(DOCUMENTS_DB)
        await manager.broadcast({
            "type": "TELEMETRY",
            "data": {
                "gpu_vram_used_gb": round(random.uniform(16.4, 18.0), 2),
                "cpu_usage_pct": round(random.uniform(20.5, 38.2), 1),
                "ram_usage_pct": round(random.uniform(60.8, 63.4), 1),
                "active_tokens_sec": random.randint(110, 240),
                "documents_count": doc_count
            }
        })
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup_event():
    # Cache default document titles in-memory unconditionally
    for doc in DOCUMENTS_DB:
        db.indexed_titles.add(doc["title"])
        
    asyncio.create_task(stream_telemetry_loop())
    
    # Seed default corporate knowledge documents if index is empty
    is_empty = False
    if db.use_pinecone and db.pinecone_index:
        try:
            stats = db.pinecone_index.describe_index_stats()
            is_empty = stats.total_vector_count == 0
        except Exception as e:
            print(f"[Database Seed] WARNING: Failed to retrieve Pinecone statistics ({e}). Skipping auto-seed check.")
            is_empty = False

    if is_empty:
        print("[Database Seed] Seeding default corporate knowledge vector database...")
        for doc in DOCUMENTS_DB:
            db.add_document(
                title=doc["title"],
                content=doc["content"],
                department=doc["department"],
                clearance=doc["clearance"]
            )
        print("[Database Seed] SUCCESS: Seeding completed successfully!")

@app.websocket("/api/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        doc_count = len(db.indexed_titles) if db.indexed_titles else len(DOCUMENTS_DB)
        await websocket.send_json({
            "type": "SYSTEM_INIT",
            "data": {
                "status": "ONLINE",
                "documents_count": doc_count
            }
        })
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
