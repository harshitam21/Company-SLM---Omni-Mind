# 🏢 ABC Industries CRM AI Operating System

A next-generation, SLM-powered **Enterprise AI Operating System** and professional B2B CRM designed specifically for **ABC Industries**. This platform features six specialized, localized department co-pilots, a Zero-Trust cybersecurity event bus, live hardware telemetry streaming via WebSockets, and a dynamic vector memory (RAG) upload registry.

The interface is engineered with a light, professional B2B SaaS CRM theme (reminiscent of premium platforms like Slack, HubSpot, and Salesforce) prioritizing visual clarity, smooth micro-animations, and modular workspace segmentation.

---

## 📸 Application Screenshot

![ABC Industries CRM AI Dashboard]

---

## ⚡ Key Engineered Features

* **💼 Specialized Localized Agents:** Independently manage operations across six key company segments:
  * **👑 Executive Strategy Agent** (Qwen-2.5-72B-Instruct)
  * **👥 HR Operations Agent** (Phi-3-Medium-128k)
  * **📈 Finance & Audit Agent** (Gemma-2-9B-IT)
  * **⚖️ Legal & Compliance Agent** (Mistral-7B-Instruct-v0.3)
  * **⚙️ Operations Control Agent** (Qwen-2.5-14B-Instruct)
  * **🛡️ Zero-Trust Security Agent** (DeepSeek-R1-Distill-Llama-8B)
* **💬 Natural, Department-Specific RAG Chatboxes:** Each division features a dedicated interactive chat pane. Responses are concise, highly conversational, and policy-focused. When a vector document is matched, it summarizes the key rules naturally and embeds a prominent verified quote box.
* **📂 Stopword-Filtered RAG Search:** Leverages an advanced search filter that strips noisy English stopwords, guaranteeing highly relevant document matching and preventing random keyword collisions.
* **⚠️ Missing Context Fallback:** If a specific question is asked that is not present in the indexed knowledge bases, the agent explicitly and politely states that the information is currently not available in indexed documents, encouraging the user to upload context.
* **📥 Live Vector Memory Ingestion:** Administrators can dynamically upload corporate PDF checklists, handbook guidelines, or agreements directly into each department's RAG segment from the UI, immediately triggering an active data-ingest pipeline and streaming telemetry.
* **🖥️ WebSocket Telemetry HUD:** Displays real-time hardware status metrics (CPU, RAM, GPU VRAM usage, and active token generation rates) by subscribing to the backend FastAPI WebSocket server.

---

## 🛠️ Technology Stack

### Frontend (React + Vite)
* **Vite + React 19** for instantaneous UI rendering and hot module reloading (HMR).
* **Lucide React** for smooth, clean vector iconography.
* **Vanilla B2B SaaS Design System** implemented entirely within [src/index.css](frontend/src/index.css), utilizing Slate boundaries, padded frames, light shadow filters, and status pulse indicators.

### Backend (FastAPI + Uvicorn)
* **FastAPI** as the high-performance asynchronous REST and WebSocket API gateway.
* **Uvicorn** for hot-reloading development server orchestration.
* **Pydantic v2** for structured request schema validations.
* **InMemory Vector Segment Simulation** tracking active corporate records for ABC Industries (including NDA templates, remote guidelines, workstation SOPs, and financial audits).

---

## 🚀 Installation & Local Startup

### System Prerequisites
* **OS:** Windows 10/11
* **Runtime:** Python 3.10+ and Node.js 18+
* **OS Shell:** PowerShell (Bypass enabled)

### All-in-One Automated Launcher
The project includes a unified PowerShell orchestrator at the root directory that automatically installs dependencies for both workspaces and boots the servers:

1. Open PowerShell in the project root directory:
   ```powershell
   cd "C:\Users\shash\Documents\SLM Project"
   ```
2. Set execution permissions (if needed) and run the dev script:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\run-dev.ps1
   ```
3. The launcher will automatically spin up:
   * **FastAPI Backend Gateway** on `http://localhost:8000`
   * **Vite Development Client** on `http://localhost:5173`
4. Open `http://localhost:5173` in your web browser.

### Manual Step-by-Step Launch

If you prefer to start the servers manually, open two terminal windows:

#### 1. Backend Server Setup
```powershell
cd "C:\Users\shash\Documents\SLM Project\backend"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Client Setup
```powershell
cd "C:\Users\shash\Documents\SLM Project\frontend"
npm install
npm run dev -- --host 0.0.0.0
```

---

## 🔒 Zero-Trust & Regulatory Standards
* **Data Scrubbing:** The Zero-Trust Security Agent automatically scans and tokenizes direct messages and files for PII (SSNs, emails, phone numbers) before vectorization.
* **Clearance Isolation:** Access to model checkpoint configurations and secure vectors requires explicit Clearance Levels (up to L5), logged immutably in system journals.
