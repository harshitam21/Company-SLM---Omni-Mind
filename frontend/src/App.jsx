import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, Cpu, Shield, Search, Database, Layers, Send, FileText, 
  Plus, LayoutDashboard, RefreshCw, Eye, Trash2
} from 'lucide-react';

const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const WEBSOCKET_URL = isLocal
  ? `ws://${window.location.hostname}:8000/api/ws/telemetry`
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/_/backend/api/ws/telemetry`;
const REST_URL = isLocal
  ? `http://${window.location.hostname}:8000/api`
  : `${window.location.protocol}//${window.location.host}/_/backend/api`;

const parseInlineFormatting = (str) => {
  const parts = str.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} style={{ fontWeight: '700', color: '#0f172a' }}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

const renderFormattedText = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    let cleanLine = line;
    
    if (cleanLine.trim() === '---') {
      return <hr key={idx} style={{ margin: '12px 0', border: 0, borderTop: '1px solid #e2e8f0' }} />;
    }
    
    if (cleanLine.startsWith('#### ') || cleanLine.startsWith('### ')) {
      const headerText = cleanLine.replace(/^(####|###)\s+/, '');
      return (
        <h4 key={idx} style={{ fontFamily: 'var(--font-sans)', fontSize: '0.88rem', fontWeight: 'bold', color: '#0f172a', marginTop: '12px', marginBottom: '6px' }}>
          {parseInlineFormatting(headerText)}
        </h4>
      );
    }
    
    if (cleanLine.trim().startsWith('• [ ]') || cleanLine.trim().startsWith('- [ ]') || cleanLine.trim().startsWith('[ ]')) {
      const todoText = cleanLine.replace(/^.*\[\s*\]\s*/, '');
      return (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '4px 0 4px 8px' }}>
          <input type="checkbox" disabled checked={false} style={{ cursor: 'not-allowed' }} />
          <span style={{ fontSize: '0.82rem', color: '#475569' }}>{parseInlineFormatting(todoText)}</span>
        </div>
      );
    }
    
    if (cleanLine.trim().startsWith('• [x]') || cleanLine.trim().startsWith('- [x]') || cleanLine.trim().startsWith('[x]')) {
      const todoText = cleanLine.replace(/^.*\[x\]\s*/, '');
      return (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '4px 0 4px 8px' }}>
          <input type="checkbox" disabled checked style={{ cursor: 'not-allowed' }} />
          <span style={{ fontSize: '0.82rem', color: '#94a3b8', textDecoration: 'line-through' }}>{parseInlineFormatting(todoText)}</span>
        </div>
      );
    }

    if (cleanLine.trim().startsWith('>')) {
      const quoteText = cleanLine.replace(/^>\s*/, '');
      return (
        <div key={idx} style={{ borderLeft: '4px solid var(--color-primary)', backgroundColor: '#eff6ff', padding: '12px 16px', borderRadius: '0 8px 8px 0', margin: '12px 0' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: '500', color: '#1e3a8a', lineHeight: '1.6', fontStyle: 'italic', display: 'block' }}>
            {parseInlineFormatting(quoteText)}
          </span>
        </div>
      );
    }

    if (cleanLine.trim().startsWith('•') || cleanLine.trim().startsWith('*')) {
      const listText = cleanLine.replace(/^(\s*•|\s*\*)\s*/, '');
      return (
        <li key={idx} style={{ marginLeft: '16px', listStyleType: 'disc', fontSize: '0.82rem', color: '#475569', margin: '4px 0' }}>
          {parseInlineFormatting(listText)}
        </li>
      );
    }
    
    return (
      <p key={idx} style={{ margin: '4px 0', fontSize: '0.85rem' }}>
        {parseInlineFormatting(cleanLine)}
      </p>
    );
  });
};

export default function App() {
  // --- STATE VARIABLES ---
  const [activeTab, setActiveTab] = useState("dashboard"); // "dashboard", "agent_hr", "agent_fin", etc.
  const [selectedDocForView, setSelectedDocForView] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [systemStatus, setSystemStatus] = useState({
    status: "ONLINE",
    gpu_vram_used_gb: 16.8,
    gpu_vram_total_gb: 24.0,
    cpu_usage_pct: 25.4,
    ram_usage_pct: 61.2,
    active_tokens_sec: 140,
    documents_count: 4
  });

  const [agents, setAgents] = useState([
    { id: "agent_exec", name: "Executive Strategy Agent", department: "Executive", avatar: "👑", status: "IDLE", model: "Qwen-2.5-72B-Instruct", clearance: 5, description: "Synthesizes multi-department reports and makes final decisions." },
    { id: "agent_hr", name: "HR Operations Agent", department: "Human Resources", avatar: "👥", status: "IDLE", model: "Phi-3-Medium-128k", clearance: 3, description: "Manages employee policies, parses organizational charts, and structures onboarding paths." },
    { id: "agent_fin", name: "Finance & Audit Agent", department: "Finance", avatar: "📈", status: "IDLE", model: "Gemma-2-9B-IT", clearance: 4, description: "Audits transactions, verifies vendor credentials, and manages budget constraints." },
    { id: "agent_legal", name: "Legal & Compliance Agent", department: "Legal", avatar: "⚖️", status: "IDLE", model: "Mistral-7B-Instruct-v0.3", clearance: 4, description: "Reviews corporate contracts, identifies liability clauses, and reviews compliance policies." },
    { id: "agent_ops", name: "Operations Control Agent", department: "Operations", avatar: "⚙️", status: "IDLE", model: "Qwen-2.5-14B-Instruct", clearance: 2, description: "Monitors internal workflow triggers, synchronizes systems, and automates operations." },
    { id: "agent_sec", name: "Zero-Trust Security Agent", department: "Cybersecurity", avatar: "🛡️", status: "ACTIVE", model: "DeepSeek-R1-Distill-Llama-8B", clearance: 5, description: "Scans queries for security clearance, logs compliance events, and prevents data leaks." }
  ]);

  // PERSISTENT CHAT HISTORY PER AGENT (Exactly like Slack channels!)
  const [chatHistory, setChatHistory] = useState({
    agent_hr: [
      { id: "m_hr_1", sender: "agent", name: "HR Operations Agent", avatar: "👥", time: "02:00:00", text: "Hello! I am the HR Operations SLM Agent. I have loaded our corporate Employee Handbook and VPN guidelines into my local memory. How can I help you today?" }
    ],
    agent_fin: [
      { id: "m_fin_1", sender: "agent", name: "Finance & Audit Agent", avatar: "📈", time: "02:00:00", text: "Greetings. I am your Finance and Audit SLM Agent. I am ready to review budgets, tax registrations, or invoicing policies." }
    ],
    agent_legal: [
      { id: "m_leg_1", sender: "agent", name: "Legal & Compliance Agent", avatar: "⚖️", time: "02:00:00", text: "State your compliance query. I am the Legal SLM Agent. I can review SLAs, Non-Disclosure Agreements, or liability limits." }
    ],
    agent_ops: [
      { id: "m_ops_1", sender: "agent", name: "Operations Control Agent", avatar: "⚙️", time: "02:00:00", text: "Operations channel active. I am monitoring active workflow pipelines. Let me know if you would like to test a workflow simulation." }
    ],
    agent_sec: [
      { id: "m_sec_1", sender: "agent", name: "Zero-Trust Security Agent", avatar: "🛡️", time: "02:00:00", text: "Zero-Trust Security layer active. I scan all queries for PII and encrypt direct message buffers. How can I protect our enterprise assets today?" }
    ],
    agent_exec: [
      { id: "m_exe_1", sender: "agent", name: "Executive Strategy Agent", avatar: "👑", time: "02:00:00", text: "Executive Console ready. I synthesize cross-department audits and authorize decisions. State your strategic request." }
    ]
  });

  const [currentMessage, setCurrentMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  // Global Ingestion Logs
  const [ingestionLogs, setIngestionLogs] = useState([
    "📥 [Ingest Pipeline] Booted vector sync for 'Handbook 2026' (Clearance: L1)",
    "📥 [Ingest Pipeline] Booted vector sync for 'Standard NDA' (Clearance: L2)",
    "📥 [Ingest Pipeline] Booted vector sync for 'Q3 Directives' (Clearance: L4)",
    "📥 [Ingest Pipeline] Booted vector sync for 'Zero-Trust Guidelines' (Clearance: L5)"
  ]);

  // Documents DB state
  const [documents, setDocuments] = useState([
    { id: "doc_1", title: "Corporate Employee Handbook 2026", department: "Human Resources", content: "All full-time employees are entitled to 25 days of paid annual leave. Remote workers must log in via the secure corporate VPN. Security training is mandatory within the first 14 days of onboarding.", clearance: 1, added_at: "2026-05-26T20:00:00" },
    { id: "doc_2", title: "Standard NDA Template - Version 4.2", department: "Legal", content: "This Non-Disclosure Agreement (NDA) binds the receiving party to protect all proprietary technical specifications, customer indices, and agent prompts. Liquidated damages for breach are valued at $500,000.", clearance: 2, added_at: "2026-05-26T20:10:00" },
    { id: "doc_3", title: "Q3 Financial Directives and Vendor Boundaries", department: "Finance", content: "Procurement of vendors with contracts exceeding $50,000 requires active secondary authorization from the VP of Finance. All transactions must be cataloged under IRS standard tax codes.", clearance: 4, added_at: "2026-05-26T20:20:00" },
    { id: "doc_4", title: "Zero-Trust Architecture Guidelines", department: "Cybersecurity", content: "Access to local SLM weight directories and training vector pools requires Level 5 security clearance. API calls must have signed JWT tokens with granular role tags.", clearance: 5, added_at: "2026-05-26T20:30:00" }
  ]);

  // Document upload form state
  const [newDocTitle, setNewDocTitle] = useState("");
  const [newDocContent, setNewDocContent] = useState("");
  const [newDocClearance, setNewDocClearance] = useState(1);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // Workflow State
  const [activeWorkflow, setActiveWorkflow] = useState(null);

  const chatEndRef = useRef(null);

  // --- WEBSOCKET FOR TELEMETRY ---
  useEffect(() => {
    let ws;
    let fallbackInterval;

    function connect() {
      ws = new WebSocket(WEBSOCKET_URL);

      ws.onopen = () => {
        setWsConnected(true);
        clearInterval(fallbackInterval);
      };

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        handleIncomingMessage(payload);
      };

      ws.onclose = () => {
        setWsConnected(false);
        startFallbackSimulation();
        setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        ws.close();
      };
    }

    function startFallbackSimulation() {
      fallbackInterval = setInterval(() => {
        setSystemStatus(prev => ({
          ...prev,
          gpu_vram_used_gb: Math.min(23.8, Math.max(15.1, prev.gpu_vram_used_gb + (Math.random() - 0.5) * 0.3)),
          cpu_usage_pct: Math.min(90, Math.max(10, prev.cpu_usage_pct + (Math.random() - 0.5) * 6)),
          ram_usage_pct: Math.min(85, Math.max(50, prev.ram_usage_pct + (Math.random() - 0.5) * 1.0)),
          active_tokens_sec: activeWorkflow ? Math.floor(Math.random() * 200) + 320 : Math.floor(Math.random() * 60) + 110
        }));
      }, 3000);
    }

    connect();

    return () => {
      if (ws) ws.close();
      clearInterval(fallbackInterval);
    };
  }, [activeWorkflow]);

  // Fetch initial documents
  useEffect(() => {
    async function loadDocs() {
      try {
        const res = await fetch(`${REST_URL}/documents`);
        if (res.ok) {
          const json = await res.json();
          setDocuments(json);
        }
      } catch (e) {
        console.error("Failed to load documents", e);
      }
    }
    loadDocs();
  }, []);

  // Auto Scroll Chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, activeTab]);

  // --- PROCESS WEBSOCKET payloads ---
  const handleIncomingMessage = (payload) => {
    const { type, data } = payload;
    switch (type) {
      case "TELEMETRY":
        setSystemStatus(prev => ({
          ...prev,
          ...data
        }));
        break;
      case "DOCUMENT_INDEXED":
        setDocuments(prev => [...prev, data.document]);
        setIngestionLogs(prev => [data.log, ...prev]);
        setSystemStatus(prev => ({
          ...prev,
          documents_count: data.total_documents
        }));
        break;
      case "DOCUMENT_DELETED":
        setDocuments(prev => prev.filter(d => d.title !== data.title));
        setIngestionLogs(prev => [data.log, ...prev]);
        setSystemStatus(prev => ({
          ...prev,
          documents_count: data.total_documents
        }));
        break;
      case "WORKFLOW_START":
        setActiveWorkflow({
          id: data.workflow_id,
          name: data.name,
          steps: data.steps,
          completed: false
        });
        break;
      case "WORKFLOW_STEP_UPDATE":
        setActiveWorkflow(prev => {
          if (!prev) return null;
          return {
            ...prev,
            steps: data.steps
          };
        });
        break;
      case "WORKFLOW_COMPLETE":
        setActiveWorkflow(prev => {
          if (!prev) return null;
          return {
            ...prev,
            steps: data.steps,
            completed: true
          };
        });
        break;
      default:
        break;
    }
  };

  const getAgentDepartmentName = (agentId) => {
    const map = {
      agent_hr: "Human Resources",
      agent_fin: "Finance",
      agent_legal: "Legal",
      agent_ops: "Operations",
      agent_sec: "Cybersecurity",
      agent_exec: "Executive"
    };
    return map[agentId] || "Global";
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      // Auto-extract title from file name (stripping extensions and underscores)
      const title = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
      setNewDocTitle(title);
    }
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    const fileInput = document.getElementById("pdf-upload-input");
    if (fileInput) fileInput.value = "";
  };

  // --- DOCUMENT INGESTION ACTION ---
  const handleDocUpload = async (e) => {
    e.preventDefault();
    if (!newDocTitle.trim()) return;
    if (!selectedFile && !newDocContent.trim()) return;

    setUploadingDoc(true);
    const deptName = getAgentDepartmentName(activeTab);
    const clearanceInt = parseInt(newDocClearance);

    if (selectedFile) {
      // File Upload Flow (Multipart FormData)
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("department", deptName);
      formData.append("clearance", clearanceInt);

      if (wsConnected) {
        try {
          const res = await fetch(`${REST_URL}/memory/upload-pdf`, {
            method: "POST",
            body: formData
          });
          if (!res.ok) throw new Error("Upload failed");
          await res.json();
        } catch (err) {
          console.error("File upload failed, falling back to local simulation", err);
          simulateLocalUpload({
            title: newDocTitle,
            content: `[Uploaded File: ${selectedFile.name}] - Simulated contents parsed successfully.`,
            department: deptName,
            clearance: clearanceInt
          });
        }
      } else {
        simulateLocalUpload({
          title: newDocTitle,
          content: `[Uploaded File: ${selectedFile.name}] - Simulated contents parsed successfully.`,
          department: deptName,
          clearance: clearanceInt
        });
      }
    } else {
      // Manual Text Ingestion Flow (JSON)
      const docData = {
        title: newDocTitle,
        content: newDocContent,
        department: deptName,
        clearance: clearanceInt
      };

      if (wsConnected) {
        try {
          const res = await fetch(`${REST_URL}/memory/upload`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(docData)
          });
          await res.json();
        } catch (err) {
          console.error("Upload API failed, simulating locally", err);
          simulateLocalUpload(docData);
        }
      } else {
        simulateLocalUpload(docData);
      }
    }

    setNewDocTitle("");
    setNewDocContent("");
    setSelectedFile(null);
    const fileInput = document.getElementById("pdf-upload-input");
    if (fileInput) fileInput.value = "";
    setUploadingDoc(false);
  };

  const simulateLocalUpload = (docData) => {
    setTimeout(() => {
      setIngestionLogs(prev => [
        `❌ [Ingest Pipeline] Ingestion FAILED: Strict Pinecone Cloud database is offline or unconfigured. Local bypass disabled.`,
        ...prev
      ]);
    }, 600);
  };

  const handleDeleteDocument = async (title, department) => {
    const confirmWipe = window.confirm(`Are you absolutely sure you want to permanently delete and wipe "${title}" from the Pinecone Cloud database? This action is irreversible!`);
    if (!confirmWipe) return;

    setDocuments(prev => prev.filter(d => d.title !== title));

    try {
      const res = await fetch(`${REST_URL}/documents/delete`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, department })
      });
      if (!res.ok) throw new Error("Delete API request failed");
      await res.json();
    } catch (err) {
      console.warn("Delete document API failed or offline. Simulating local soft-delete.", err);
      setIngestionLogs(prev => [
        `❌ [Ingest Pipeline] Wiped document: '${title}' from local view. Pinecone cleanup requires online connection.`,
        ...prev
      ]);
    }
  };

  const fUuid = () => Math.random().toString(36).substring(2, 9);

  // --- DEDICATED DIRECT CHATBOX SUBMIT ---
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!currentMessage.trim() || isSending) return;

    const query = currentMessage;
    setCurrentMessage("");
    setIsSending(true);

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    const userMessageId = fUuid();
    const userMsg = {
      id: userMessageId,
      sender: "user",
      name: "You",
      avatar: "👤",
      time: timeStr,
      text: query
    };

    setChatHistory(prev => ({
      ...prev,
      [activeTab]: [...prev[activeTab], userMsg]
    }));

    // Unconditionally attempt the REST API chat endpoint first, falling back to simulated chat only on absolute HTTP network failure!
    try {
      const res = await fetch(`${REST_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: activeTab, message: query })
      });
      if (!res.ok) throw new Error("REST Chat API failed");
      const json = await res.json();
      
      const nowAgent = new Date();
      const timeStrAgent = `${String(nowAgent.getHours()).padStart(2, '0')}:${String(nowAgent.getMinutes()).padStart(2, '0')}:${String(nowAgent.getSeconds()).padStart(2, '0')}`;
      
      setChatHistory(prev => ({
        ...prev,
        [activeTab]: [
          ...prev[activeTab],
          {
            id: fUuid(),
            sender: "agent",
            name: agents.find(a => a.id === activeTab).name,
            avatar: agents.find(a => a.id === activeTab).avatar,
            time: timeStrAgent,
            thinking_steps: json.thinking_steps,
            text: json.response
          }
        ]
      }));
    } catch (err) {
      console.warn("Real Chat REST API failed. Initiating smart on-premise local simulation.", err);
      simulateLocalChat(query);
    }
    
    setIsSending(false);
  };

  const simulateLocalChat = (query) => {
    const activeAgent = agents.find(a => a.id === activeTab);
    const departmentName = getAgentDepartmentName(activeTab);
    
    setTimeout(() => {
      const thinkingSteps = [
        `🔐 [Zero-Trust Gate] Validating security clearances for resource query...`,
      ];
      
      const query_clean = query.strip ? query.strip().toLowerCase() : query.trim().toLowerCase();
      const query_lower = query_clean;
      const queryWords = query_lower.split(/\s+/).map(w => w.replace(/[.,!?"']/g, ""));
      
      // Determine skip RAG conditions
      const is_greeting = ["hi", "hello", "hey", "greetings", "yo", "good morning", "good afternoon", "good evening", "sup"].some(g => queryWords.includes(g));
      const is_asking_identity = ["who are you", "what are you", "your name", "tell me about yourself"].some(x => query_lower.includes(x));
      const is_asking_skills = ["what can you do", "what are your skills", "your capabilities", "skills", "help", "how can you help"].some(x => query_lower.includes(x));
      const is_positive_ack = ["thanks", "thank you", "perfect", "great", "awesome", "ok", "got it", "cool", "clear"].some(ack => queryWords.includes(ack));
      const is_small_talk = ["how are you", "how's it going", "how are you doing", "are you real", "are you human"].some(x => query_lower.includes(x));
      const is_asking_for_docs = ["what documents", "what files", "list documents", "list files", "show documents", "show files", "which documents", "what all documents", "what do you have", "what is in your database", "what is indexed"].some(x => query_lower.includes(x));
      
      const skip_rag = query_lower.length <= 3 || is_greeting || is_asking_identity || is_asking_skills || is_positive_ack || is_small_talk || is_asking_for_docs;
      
      let responseText = "";
      
      if (skip_rag) {
        thinkingSteps.push(
          `🔍 [Vector Search] Input query detected as conversational, greeting, or capability request. Bypassing database search.`
        );
        thinkingSteps.push(
          `🧠 [Context Injection] Routing query to active local divisional parameters.`
        );
        
        if (is_asking_for_docs) {
          const deptDocs = documents.filter(d => d.department.toLowerCase() === departmentName.toLowerCase());
          if (deptDocs.length > 0) {
            const docList = deptDocs.map(d => `• **${d.title}** (Clearance: L${d.clearance})`).join("\n");
            responseText = `I currently have access to the following local memory files in the **${departmentName}** segment:\n\n${docList}\n\nAsk me any questions about their specific contents!`;
          } else {
            responseText = `I currently do not have any documents indexed in the local **${departmentName}** vector pool. You can upload a PDF, DOCX, or TXT file on the right!`;
          }
        } else if (is_greeting) {
          responseText = `Hello! I am your **${activeAgent.name}** supporting the **${departmentName}** division at ABC Industries. I am online and ready to assist you with policies, logs, or compliance review.`;
        } else if (is_asking_identity || is_asking_skills) {
          const skills_md = activeAgent.skills.map(skill => `• **${skill}**`).join("\n");
          responseText = `### ${activeAgent.avatar} ${activeAgent.name.toUpperCase()} PROFILE & HUD\n\nI am the specialized **${activeAgent.name}** for the **${departmentName}** division.\n\n#### ⚙️ Technical Vitals\n• **Model**: \`${activeAgent.model}\` (Offline Local Fallback)\n• **Clearance**: \`Level L${activeAgent.clearance}\` Authenticated\n\n#### 🧠 Domain Skills\n${skills_md}\n\n*${activeAgent.description}*`;
        } else if (is_positive_ack) {
          responseText = `You're very welcome! I'm happy to help. 😊\n\nIs there anything else you need checked or processed regarding the **${departmentName}** records?`;
        } else if (is_small_talk) {
          responseText = `I am functioning at peak efficiency! Operating as a local \`${activeAgent.model}\` SLM co-pilot. Standard operational systems are 100% nominal. How can I assist you with your department tasks today?`;
        } else {
          responseText = `Hello! How can I support the **${departmentName}** division operations today?`;
        }
      } else {
        thinkingSteps.push(`🔍 [Vector Search] Matching query tokens against local ${departmentName} memory collections...`);
        const deptDocs = documents.filter(d => d.department.toLowerCase() === departmentName.toLowerCase());
        
        // Find best match by checking overlap of keywords
        let bestMatch = null;
        let highestScore = 0;
        const queryWordsSearch = query_lower.split(/\s+/).filter(w => w.length > 3);
        
        for (const doc of deptDocs) {
          const docContentLower = doc.content.toLowerCase();
          let score = 0;
          for (const w of queryWordsSearch) {
            if (docContentLower.includes(w)) score++;
          }
          if (score > highestScore) {
            highestScore = score;
            bestMatch = doc;
          }
        }
        
        // Require score overlap to be >= 1 for genuine RAG match
        if (bestMatch && highestScore >= 1) {
          thinkingSteps.push(`🧠 [Context Injection] Found local memory match: '${bestMatch.title}'. Score weight: ${highestScore}.`);
          
          // Try to extract relevant sentences
          const sentences = bestMatch.content.split(/[.?!]\s+/);
          const matchedSentences = sentences.filter(s => {
            const sLower = s.toLowerCase();
            return queryWordsSearch.some(w => sLower.includes(w));
          });
          
          const answer = matchedSentences.length > 0 ? matchedSentences.slice(0, 2).join(". ") + "." : bestMatch.content;
          responseText = `Based on the local policy document **${bestMatch.title}**, here is what I found:\n\n${answer}\n\n*(Source: ${bestMatch.title})*`;
        } else {
          thinkingSteps.push(`🧠 [Context Injection] Searching global shared enterprise indices. No hot direct matches found; routing to conversational weights.`);
          
          const dept = departmentName.toLowerCase();
          if (dept.includes("human resources")) {
            if (query_lower.includes("remote") || query_lower.includes("hybrid") || query_lower.includes("hours") || query_lower.includes("work")) {
              responseText = "### 👥 HR OPERATIONS CO-PILOT ADVISORY (LOCAL)\n\nAt ABC Industries, our employees are entitled to a **Remote-Hybrid Model** consisting of **3 days remote and 2 days in-office**.\n\n**Core Guidelines**:\n• **Core Hours**: 10:00 AM to 4:00 PM EST.\n• **VPN Protocol**: Strictly use the secure corporate Zero-Trust VPN gateway.\n• **Ethics Standard**: Professional communications are required on all Slack channels.\n\n*(Source: HR Remote Work & Code of Conduct Policy)*";
            } else if (query_lower.includes("leave") || query_lower.includes("pto") || query_lower.includes("vacation") || query_lower.includes("benefits") || query_lower.includes("offer")) {
              responseText = "### 👥 HR OPERATIONS BENEFITS SUMMARY (LOCAL)\n\nUnder standard ABC Industries benefits protocols:\n• **PTO**: 25 days of Paid Time Off annually.\n• **Insurance**: Comprehensive PPO health package.\n• **Retirement Match**: 401(k) match up to 5%.\n• **Equity options**: 4-year vesting with a 1-year cliff.\n\n*(Source: Standard Offer Letter & Benefits Package)*";
            } else if (query_lower.includes("onboard") || query_lower.includes("new hire") || query_lower.includes("training") || query_lower.includes("probation")) {
              responseText = "### 👥 HR NEW HIRE ONBOARDING ROADMAP (LOCAL)\n\nStandard onboarding checkpoints:\n• **Day 1**: Workstation provisioning and legal compliance check.\n• **Day 3**: Secure active directory setup and VPN synchronization.\n• **Day 14**: Mandatory Cybersecurity Training and Zero-Trust credential issuance.\n\n*(Source: New Hire Onboarding SOP)*";
            } else {
              responseText = `I searched our secure local **${departmentName}** registers for **"${query}"** but couldn't find a direct document segment.\n\nAs your co-pilot, I can assist you once you upload the handbook or policy PDF in the memory panel on the right!`;
            }
          } else if (dept.includes("finance")) {
            responseText = `### 📈 FINANCE POLICY COMPLIANCE (LOCAL)\n\nCorporate financial guidelines:\n• **Expense approvals**: Automated under $500; Secondary written authorization by the VP of Finance required for procurement over $50,000.\n• **Tax cataloging**: All transactions must use standard Subchapter C IRS tax codes.\n• **Payment terms**: Standard vendor scheduling is Net-30 from validated deliverables.`;
          } else if (dept.includes("legal")) {
            responseText = `### ⚖️ LEGAL COMPLIANCE PROTOCOLS (LOCAL)\n\nCorporate parameters registry:\n• **NDAs**: Protecting proprietary technical specs, indices, and prompts. Default breach damages valued at $500,000.\n• **SLAs**: Guaranteeing 99.9% availability uptime, downtime credits at 5% of monthly fees/hour, and liability caps set to preceding 6 months of payments.`;
          } else if (dept.includes("cybersecurity")) {
            responseText = `### 🛡️ ZERO-TRUST SECURITY STANDARDS (LOCAL)\n\nCybersecurity enforcement:\n• **Weight isolation**: Weight directories and training indices run in sandboxed environments (Level 5 clearance).\n• **Access gates**: RBAC/ABAC token verification for all operations.\n• **Privacy**: PII Scrubbing of Social Security numbers, phone numbers, and emails before vector storage.`;
          } else {
            responseText = `I searched our local secure **${departmentName}** database for **"${query}"**.\n\n⚠️ **This specific information is currently not found in our indexed document chunks.**\n\nIf you have a manual, SOP, or policy document, you can upload it using the **Ingest to Memory** panel on the right. I will instantly build a vector index and answer your questions!`;
          }
        }
      }
      
      thinkingSteps.push(`⚙️ [Model Gate] Forwarding query + clearance L${activeAgent.clearance} context to local quantized model [${activeAgent.model}].`);

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

      setChatHistory(prev => ({
        ...prev,
        [activeTab]: [
          ...prev[activeTab],
          {
            id: fUuid(),
            sender: "agent",
            name: activeAgent.name,
            avatar: activeAgent.avatar,
            time: timeStr,
            thinking_steps: thinkingSteps,
            text: responseText
          }
        ]
      }));
    }, 1500);
  };

  const triggerWorkflowSimulation = async (type) => {
    if (wsConnected) {
      try {
        await fetch(`${REST_URL}/workflows/trigger`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workflow_type: type, initiator: "CRM Control Dashboard" })
        });
      } catch (e) {
        console.error("Workflow trigger failed", e);
      }
    }
  };

  const getClearanceClass = (level) => {
    if (level <= 1) return "tag-clearance tag-clearance-low";
    if (level <= 3) return "tag-clearance tag-clearance-med";
    if (level <= 4) return "tag-clearance tag-clearance-high";
    return "tag-clearance tag-clearance-top";
  };

  // --- RENDER DYNAMIC LAYOUT ---
  return (
    <div className="app-container">
      
      {/* LEFT SIDEBAR PANEL */}
      <aside className="sidebar-panel">
        <div>
          {/* Logo HUD Branding */}
          <div className="sidebar-logo">
            <div className="logo-box">Ω</div>
            <div>
              <span className="logo-title block">OMNIMIND</span>
              <span className="logo-sub block">ENTERPRISE CRM OS</span>
            </div>
          </div>

          <span className="sidebar-section-title">Workspace Core</span>
          <button 
            onClick={() => setActiveTab("dashboard")}
            className={`sidebar-item ${activeTab === "dashboard" ? "active" : ""}`}
          >
            <LayoutDashboard size={14} />
            <span>General Dashboard</span>
          </button>

          <span className="sidebar-section-title">Department Agents</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {agents.map((a) => (
              <button 
                key={a.id}
                onClick={() => setActiveTab(a.id)}
                className={`sidebar-item ${activeTab === a.id ? "active" : ""}`}
              >
                <span>{a.avatar}</span>
                <span className="truncate">{a.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Sidebar Footer compute info */}
        <div className="sidebar-footer">
          <div className="compute-vitals">
            <div className="compute-vitals-header">
              <span>COMPUTE ENGINE</span>
              <span className="vital-led"></span>
            </div>
            <div className="vital-row">VRAM: {systemStatus.gpu_vram_used_gb.toFixed(1)} GB / 24 GB</div>
            <div className="vital-row">CPU: {systemStatus.cpu_usage_pct.toFixed(0)}%</div>
            <div className="vital-row">DOCS: {systemStatus.documents_count}</div>
          </div>
        </div>
      </aside>

      {/* MAIN VIEWPORT CANVAS */}
      <main className="main-viewport">
        
        {/* TOP STATUS BAR */}
        <header className="top-navbar">
          <span className="top-navbar-title">
            {activeTab === "dashboard" ? "Global System Command Center" : `${agents.find(a => a.id === activeTab).department} Workspace`}
          </span>
          
          <div className="top-navbar-stats">
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={12} className="text-emerald-500" />
              <span>Tokens/sec: {systemStatus.active_tokens_sec}</span>
            </span>
            <span style={{ margin: '0 8px', color: '#cbd5e1' }}>|</span>
            <span>clearance context: L1-L5 APPROVED</span>
          </div>
        </header>

        {/* WORKSPACE BODY AREA */}
        <div className="body-container">
          
          {/* TAB 1: GENERAL DASHBOARD PAGE */}
          {activeTab === "dashboard" && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* TOP SUMMARY STATS WIDGET ROW */}
              <div className="metrics-row">
                <div className="stat-widget">
                  <span className="stat-label">Shared Memory Size</span>
                  <div className="stat-value-container">
                    <span className="stat-value">{systemStatus.documents_count}</span>
                    <span className="stat-sub">Indexed Files</span>
                  </div>
                </div>

                <div className="stat-widget">
                  <span className="stat-label">Inference Gate</span>
                  <div className="stat-value-container">
                    <span className="stat-value" style={{ fontSize: '1.05rem', fontWeight: 600 }}>Local Quantized SLMs</span>
                  </div>
                  <span className="text-[10px] text-emerald-600 font-mono font-bold" style={{ display: 'block', marginTop: '4px' }}>vLLM ACTIVE PIPELINE</span>
                </div>

                <div className="stat-widget">
                  <span className="stat-label">CPU Core Load</span>
                  <div>
                    <span className="stat-value">{systemStatus.cpu_usage_pct.toFixed(0)}%</span>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill bg-blue-500" style={{ width: `${systemStatus.cpu_usage_pct}%` }}></div>
                    </div>
                  </div>
                </div>

                <div className="stat-widget">
                  <span className="stat-label">GPU VRAM Cache</span>
                  <div>
                    <span className="stat-value" style={{ fontSize: '1.15rem' }}>{systemStatus.gpu_vram_used_gb.toFixed(1)} GB / 24 GB</span>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill bg-violet-500" style={{ width: `${(systemStatus.gpu_vram_used_gb / 24) * 100}%` }}></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* GRID FOR DOCS INDEX AND LOGS */}
              <div className="workspace-grid">
                
                {/* GLOBAL FILES INDEX */}
                <div className="crm-card">
                  <div className="crm-card-header">
                    <h3 className="crm-card-title">
                      <Database size={14} className="text-blue-500" style={{ marginRight: '6px' }} /> shared organizational memory registers
                    </h3>
                  </div>
                  
                  <div className="table-scroll">
                    <table className="crm-table">
                      <thead>
                        <tr>
                          <th>Document Title</th>
                          <th>Department segment</th>
                          <th>Clearance tag</th>
                          <th style={{ textAlign: 'right' }}>Data status</th>
                          <th style={{ textAlign: 'center', width: '90px' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {documents.map((doc) => (
                          <tr key={doc.id}>
                            <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <FileText size={14} className="text-blue-500" />
                              <span>{doc.title}</span>
                            </td>
                            <td>
                              <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] uppercase font-bold text-slate-600">
                                {doc.department}
                              </span>
                            </td>
                            <td>
                              <span className={getClearanceClass(doc.clearance)}>
                                Level {doc.clearance}
                              </span>
                            </td>
                            <td style={{ textAlign: 'right', color: '#059669', fontWeight: 'bold', fontFamily: 'monospace' }}>INDEXED // RAG_POOL</td>
                            <td style={{ textAlign: 'center' }}>
                              <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                <button 
                                  onClick={() => setSelectedDocForView(doc)}
                                  title="View document content"
                                  style={{ padding: '4px', display: 'flex', alignItems: 'center', backgroundColor: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe', borderRadius: '4px', cursor: 'pointer' }}
                                >
                                  <Eye size={12} />
                                </button>
                                <button 
                                  onClick={() => handleDeleteDocument(doc.title, doc.department)}
                                  title="Delete from database"
                                  style={{ padding: '4px', display: 'flex', alignItems: 'center', backgroundColor: '#fef2f2', color: '#ef4444', border: '1px solid #fca5a5', borderRadius: '4px', cursor: 'pointer' }}
                                >
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* INGEST TERMINAL STREAM */}
                <div className="crm-card">
                  <div className="crm-card-header">
                    <h3 className="crm-card-title">
                      <Activity size={14} className="text-blue-500" style={{ marginRight: '6px' }} /> live Ingest logs
                    </h3>
                  </div>
                  
                  <div style={{ maxHeight: '220px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '11px', color: '#64748b', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {ingestionLogs.map((log, idx) => (
                      <div key={idx} style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '6px' }}>
                        {log}
                      </div>
                    ))}
                  </div>
                </div>

              </div>

              {/* CRM WORKFLOW AUTOMATION TRIGGERS */}
              <div className="crm-card">
                <div className="crm-card-header">
                  <h3 className="crm-card-title">
                    <Layers size={14} className="text-blue-500" style={{ marginRight: '6px' }} /> autonomous cross-agent workflows
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '16px' }}>
                  <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '144px' }}>
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1e293b', display: 'block' }}>ONBOARDING PIPELINE</span>
                      <p style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>Runs HR charting, drafts/evaluates NDAs, budgets hardware, and setups security VPN keys.</p>
                    </div>
                    <button 
                      onClick={() => triggerWorkflowSimulation("ONBOARDING")}
                      disabled={activeWorkflow && !activeWorkflow.completed}
                      className="btn-crm"
                      style={{ width: '100%' }}
                    >
                      Trigger Workflow Swarm
                    </button>
                  </div>

                  <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '144px' }}>
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1e293b', display: 'block' }}>VENDOR COMPLIANCE AUDIT</span>
                      <p style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>Extracts vendor details, parses legal liability bounds, and audits tax compliance.</p>
                    </div>
                    <button 
                      onClick={() => triggerWorkflowSimulation("VENDOR_COMPLIANCE")}
                      disabled={activeWorkflow && !activeWorkflow.completed}
                      className="btn-crm"
                      style={{ width: '100%' }}
                    >
                      Trigger Workflow Swarm
                    </button>
                  </div>

                  <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '144px' }}>
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1e293b', display: 'block' }}>Q3 BUDGET ALLOCATIONS</span>
                      <p style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>Analyzes spending logs, syncs department requirements, and approves strategic budget briefs.</p>
                    </div>
                    <button 
                      onClick={() => triggerWorkflowSimulation("BUDGET_APPROVAL")}
                      disabled={activeWorkflow && !activeWorkflow.completed}
                      className="btn-crm"
                      style={{ width: '100%' }}
                    >
                      Trigger Workflow Swarm
                    </button>
                  </div>
                </div>

                {activeWorkflow && (
                  <div className="workflow-status-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 600, color: '#475569' }}>Active Workflow: <span style={{ fontFamily: 'monospace', color: '#2563eb', fontWeight: 'bold' }}>{activeWorkflow.name}</span></span>
                      <span className={`tag-clearance ${activeWorkflow.completed ? 'tag-clearance-high' : 'tag-clearance-med animate-pulse'}`} style={{ fontSize: '9px', fontWeight: 'bold' }}>
                        {activeWorkflow.completed ? 'COMPLETED' : 'ACTIVE_STEPS_COMPILING'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {activeWorkflow.steps.map((s, idx) => (
                        <div 
                          key={idx} 
                          className={`progress-bar-bg`}
                          style={{ flex: 1, height: '6px', margin: 0, overflow: 'hidden' }}
                        >
                          <div 
                            className={`progress-bar-fill ${s.status === "COMPLETED" ? 'bg-emerald-500' : s.status === "IN_PROGRESS" ? 'bg-blue-500' : 'bg-slate-200'}`}
                            style={{ width: s.status === "COMPLETED" || s.status === "IN_PROGRESS" ? '100%' : '0%' }}
                          ></div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 2: INDIVIDUAL DEPARTMENT WORKSPACE PAGES */}
          {activeTab !== "dashboard" && (
            <div className="chat-split-view">
              
              {/* LEFT HALF (Chatbox Workspace) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* Agent Header card */}
                <div className="crm-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '1.8rem' }}>{agents.find(a => a.id === activeTab).avatar}</span>
                    <div>
                      <h2 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#1e293b' }}>{agents.find(a => a.id === activeTab).name}</h2>
                      <p style={{ fontSize: '10px', color: '#64748b', fontFamily: 'monospace', marginTop: '2px' }}>
                        <span style={{ color: '#2563eb', fontWeight: 'bold' }}>{agents.find(a => a.id === activeTab).model}</span> // Clearance Context: Level 1-Level {agents.find(a => a.id === activeTab).clearance} Approved
                      </p>
                    </div>
                  </div>

                  <span className={getClearanceClass(agents.find(a => a.id === activeTab).clearance)}>
                    Clearance Level {agents.find(a => a.id === activeTab).clearance}
                  </span>
                </div>

                {/* DEDICATED DEPARTMENT CHATBOX */}
                <div className="chat-box-card">
                  
                  {/* MESSAGES CHAT LOG FEED */}
                  <div className="chat-box-feed">
                    {chatHistory[activeTab].map((msg) => (
                      <div key={msg.id} className="msg-wrapper">
                        
                        {/* Sender details */}
                        <div className={`msg-header ${msg.sender === 'user' ? 'msg-header-user' : ''}`}>
                          {msg.sender !== 'user' && <span>{msg.avatar}</span>}
                          <span>{msg.name}</span>
                          <span>•</span>
                          <span>{msg.time}</span>
                        </div>

                        {/* Internal agent thought chain details */}
                        {msg.sender === 'agent' && msg.thinking_steps && (
                          <details className="thought-accordion">
                            <summary className="thought-summary">
                              <span>🔍 VIEW REASONING STEPS</span>
                            </summary>
                            <div className="thought-details">
                              {msg.thinking_steps.map((step, idx) => (
                                <div key={idx}>{step}</div>
                              ))}
                            </div>
                          </details>
                        )}

                        {/* Message bubble */}
                        <div className={msg.sender === 'user' ? 'msg-bubble-user' : 'msg-bubble-agent'}>
                          {msg.sender === 'user' ? msg.text : renderFormattedText(msg.text)}
                        </div>

                      </div>
                    ))}
                    
                    {/* Sending loading buffer */}
                    {isSending && (
                      <div className="msg-wrapper">
                        <div className="msg-header">
                          <span>{agents.find(a => a.id === activeTab).avatar}</span>
                          <span>{agents.find(a => a.id === activeTab).name}</span>
                          <span>•</span>
                          <span className="animate-pulse">Thinking...</span>
                        </div>
                        <div className="msg-bubble-agent" style={{ color: '#64748b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <RefreshCw size={12} className="animate-spin text-blue-500" />
                          <span>Searching Pinecone Cloud vector indices and compiling model response...</span>
                        </div>
                      </div>
                    )}
                    
                    <div ref={chatEndRef}></div>
                  </div>

                  {/* BOTTOM INPUT BAR FOR CHATBOX */}
                  <form onSubmit={handleSendMessage} className="chat-input-bar">
                    <input 
                      type="text" 
                      value={currentMessage}
                      onChange={(e) => setCurrentMessage(e.target.value)}
                      placeholder={`Message ${agents.find(a => a.id === activeTab).name}...`}
                      className="chat-input-field"
                    />
                    <button 
                      type="submit" 
                      disabled={!currentMessage.trim() || isSending}
                      className="btn-crm"
                    >
                      <Send size={12} />
                    </button>
                  </form>

                </div>

              </div>

              {/* RIGHT HALF (Knowledge base & dynamic upload) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* FILE INGESTION FORM */}
                <div className="crm-card" style={{ marginBottom: 0 }}>
                  <div className="crm-card-header">
                    <h3 className="crm-card-title">
                      <Plus size={14} className="text-blue-500" style={{ marginRight: '4px' }} /> Ingest to Memory
                    </h3>
                  </div>

                  <form onSubmit={handleDocUpload}>
                    <div className="form-group" style={{ marginBottom: '12px' }}>
                      <label className="form-label">Upload Document (.pdf, .docx, .txt)</label>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <input 
                          type="file" 
                          accept=".pdf,.docx,.txt,.text"
                          id="pdf-upload-input"
                          onChange={handleFileChange}
                          className="form-input"
                          style={{ padding: '4px', fontSize: '11px', flex: 1, border: '1px solid #cbd5e1', borderRadius: '4px' }}
                        />
                        {selectedFile && (
                          <button 
                            type="button" 
                            onClick={clearSelectedFile}
                            className="btn-crm"
                            style={{ padding: '6px 10px', fontSize: '10px', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Document Title</label>
                      <input 
                        type="text" 
                        value={newDocTitle}
                        onChange={(e) => setNewDocTitle(e.target.value)}
                        placeholder="e.g. Travel Expense Rules..." 
                        required
                        className="form-input"
                      />
                    </div>

                    {!selectedFile && (
                      <div className="form-group">
                        <label className="form-label">Text Content</label>
                        <textarea 
                          rows={4}
                          value={newDocContent}
                          onChange={(e) => setNewDocContent(e.target.value)}
                          placeholder="Paste document text context..." 
                          required={!selectedFile}
                          className="form-textarea"
                        ></textarea>
                      </div>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '12px' }}>
                      <div>
                        <label className="form-label">Clearance</label>
                        <select 
                          value={newDocClearance}
                          onChange={(e) => setNewDocClearance(e.target.value)}
                          className="form-input"
                          style={{ padding: '6px 8px', fontSize: '11px' }}
                        >
                          <option value={1}>Level 1 (Public)</option>
                          <option value={2}>Level 2 (Internal)</option>
                          <option value={3}>Level 3 (Secret)</option>
                          <option value={4}>Level 4 (Top Secret)</option>
                          <option value={5}>Level 5 (Owner)</option>
                        </select>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'end' }}>
                        <button 
                          type="submit" 
                          disabled={uploadingDoc || !newDocTitle.trim() || (!selectedFile && !newDocContent.trim())}
                          className="btn-crm"
                          style={{ width: '100%', padding: '8px 0', fontSize: '11px' }}
                        >
                          {uploadingDoc ? <RefreshCw size={11} className="animate-spin" /> : <Plus size={11} />}
                          <span>Upload File</span>
                        </button>
                      </div>
                    </div>
                  </form>
                </div>

                {/* DEPARTMENT KNOWLEDGE BASE FILES */}
                <div className="crm-card" style={{ flex: 1, minHeight: '260px', display: 'flex', flexDirection: 'column', marginBottom: 0 }}>
                  <div className="crm-card-header">
                    <h3 className="crm-card-title">
                      <Database size={14} className="text-blue-500" style={{ marginRight: '4px' }} /> local knowledge base
                    </h3>
                  </div>

                  <div className="scrolling-docs-list">
                    {documents.filter(d => d.department.toLowerCase() === getAgentDepartmentName(activeTab).toLowerCase()).length > 0 ? (
                      documents
                        .filter(d => d.department.toLowerCase() === getAgentDepartmentName(activeTab).toLowerCase())
                        .map((doc) => (
                          <div key={doc.id} className="kb-file-card" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', borderRadius: '6px', border: '1px solid #e2e8f0', backgroundColor: '#fff', position: 'relative' }}>
                            <div className="kb-file-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', maxWidth: '70%' }}>
                                <FileText size={12} className="text-blue-500" />
                                <span className="kb-file-title truncate" style={{ fontWeight: 600, fontSize: '0.8rem', color: '#1e293b' }} title={doc.title}>{doc.title}</span>
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span className={getClearanceClass(doc.clearance)} style={{ fontSize: '8px', padding: '2px 4px' }}>
                                  L{doc.clearance}
                                </span>
                                <button 
                                  onClick={() => setSelectedDocForView(doc)}
                                  title="View Full Content"
                                  style={{ padding: '3px', display: 'flex', alignItems: 'center', backgroundColor: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe', borderRadius: '3px', cursor: 'pointer' }}
                                >
                                  <Eye size={10} />
                                </button>
                                <button 
                                  onClick={() => handleDeleteDocument(doc.title, doc.department)}
                                  title="Delete Document"
                                  style={{ padding: '3px', display: 'flex', alignItems: 'center', backgroundColor: '#fef2f2', color: '#ef4444', border: '1px solid #fca5a5', borderRadius: '3px', cursor: 'pointer' }}
                                >
                                  <Trash2 size={10} />
                                </button>
                              </div>
                            </div>
                            <p className="kb-file-content" style={{ fontSize: '10px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', margin: 0 }}>
                              {doc.content}
                            </p>
                          </div>
                        ))
                    ) : (
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px', border: '1px dashed #cbd5e1', borderRadius: '6px', textAlign: 'center' }}>
                        <Database size={20} className="text-slate-300" style={{ marginBottom: '6px' }} />
                        <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#94a3b8' }}>Memory Segment Empty</span>
                      </div>
                    )}
                  </div>
                </div>

              </div>

            </div>
          )}

        </div>

        {/* CRM FOOTER */}
        <footer className="crm-footer">
          <span>© 2026 OMNIMIND ENTERPRISE SAS WORKSPACE. ALL RIGHTS ENCRYPTED.</span>
          <span>ZERO-TRUST MODEL PROTECTION STATUS: OPERATIONAL</span>
        </footer>

      </main>

      {/* PREMIUM GLASSMORPHIC DOCUMENT INSPECTION VIEW MODAL */}
      {selectedDocForView && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          animation: 'fadeIn 0.2s ease-out'
        }}>
          <div style={{
            width: '90%',
            maxWidth: '680px',
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            border: '1px solid #e2e8f0',
            display: 'flex',
            flexDirection: 'column',
            maxHeight: '80vh',
            overflow: 'hidden'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid #e2e8f0',
              backgroundColor: '#f8fafc',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={18} className="text-blue-500" />
                <div style={{ textAlign: 'left' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#0f172a', margin: 0 }}>
                    {selectedDocForView.title}
                  </h3>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px' }}>
                    <span style={{ fontSize: '9px', fontWeight: 'bold', textTransform: 'uppercase', padding: '1px 4px', backgroundColor: '#e2e8f0', borderRadius: '3px', color: '#475569' }}>
                      {selectedDocForView.department}
                    </span>
                    <span className={getClearanceClass(selectedDocForView.clearance)} style={{ fontSize: '8px', padding: '1px 4px' }}>
                      Clearance L{selectedDocForView.clearance}
                    </span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedDocForView(null)}
                style={{
                  border: 'none',
                  backgroundColor: 'transparent',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '1.2rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '4px'
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={{
              padding: '24px',
              overflowY: 'auto',
              flex: 1,
              backgroundColor: '#ffffff',
              lineHeight: '1.6',
              fontSize: '0.88rem',
              color: '#334155',
              textAlign: 'left'
            }}>
              {renderFormattedText(selectedDocForView.content)}
            </div>

            {/* Modal Footer */}
            <div style={{
              padding: '12px 20px',
              borderTop: '1px solid #e2e8f0',
              backgroundColor: '#f8fafc',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '10px'
            }}>
              <button 
                onClick={() => setSelectedDocForView(null)}
                className="btn-crm"
                style={{ padding: '6px 16px', fontSize: '11px' }}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
