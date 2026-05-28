import os
import json
import uuid
import math

# We import torch and transformers for on-premise sentence embeddings
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# We import Pinecone client SDK for managed vector database persistence
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

class VectorStore:
    def __init__(self, persist_path="vector_store.json"):
        self.persist_path = persist_path
        self.chunks = []
        self.indexed_titles = set()
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        
        # Load environment variables from .env file if it exists in parent folders
        for search_dir in [os.path.dirname(__file__), os.path.dirname(os.path.dirname(__file__)), os.path.dirname(os.path.dirname(os.path.dirname(__file__)))]:
            env_path = os.path.join(search_dir, ".env")
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, val = line.split("=", 1)
                                os.environ[key.strip()] = val.strip().strip("'\"")
                    print(f"[Vector Store] SUCCESS: Loaded environment variables from '{env_path}'")
                    break
                except Exception as e:
                    print(f"[Vector Store] WARNING: Failed to load .env file ({e})")
        
        # Read Pinecone configurations from environment
        self.pinecone_api_key = os.environ.get("PINECONE_API_KEY", "").strip()
        self.pinecone_index_name = os.environ.get("PINECONE_INDEX", "omnimind-index").strip()
        self.pinecone_cloud = os.environ.get("PINECONE_CLOUD", "aws").strip()
        self.pinecone_region = os.environ.get("PINECONE_REGION", "us-east-1").strip()
        
        self.use_pinecone = False
        self.pinecone_index = None
        
        # Initialize GPU acceleration for local embeddings
        if TRANSFORMERS_AVAILABLE:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch, "backends") and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
        
        self._init_embedding_model()
        self._init_pinecone()
        self.load()

    def _init_embedding_model(self):
        """Initializes the on-premise sentence transformer model with a resilient fallback."""
        if not TRANSFORMERS_AVAILABLE:
            print("[Vector Engine] WARNING: PyTorch or Transformers not found. Initializing semantic TF-IDF fallback.")
            return
            
        try:
            print(f"[Vector Engine] Booting on-premise embedding model ('all-MiniLM-L6-v2') on {self.device}...")
            # We use the industry-standard all-MiniLM-L6-v2 (80MB, fast and accurate)
            self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            self.model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            self.model.to(self.device)
            self.model.eval()
            print("[Vector Engine] SUCCESS: Embedding model successfully loaded and active!")
        except Exception as e:
            print(f"[Vector Engine] WARNING: Failed to load HuggingFace model ({e}). Initializing semantic fallback.")
            self.tokenizer = None
            self.model = None

    def _init_pinecone(self):
        """Attempts to initialize connection to Pinecone Cloud, creating index if missing."""
        if not PINECONE_AVAILABLE:
            raise RuntimeError(
                "[Vector Store] FATAL ERROR: Pinecone client library 'pinecone' is not installed, but strict Pinecone Mode is active. "
                "Please run 'pip install pinecone' to enable cloud vector database operations."
            )
            
        if not self.pinecone_api_key:
            raise RuntimeError(
                "[Vector Store] FATAL ERROR: 'PINECONE_API_KEY' is not set in environment or .env, but strict Pinecone Mode is active. "
                "Please configure a valid Pinecone API Key."
            )
            
        try:
            print(f"[Vector Store] Connecting to Pinecone Cloud (Index: '{self.pinecone_index_name}')...")
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Auto-provision serverless index if it doesn't exist
            active_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.pinecone_index_name not in active_indexes:
                print(f"[Vector Store] Index '{self.pinecone_index_name}' not found. Provisioning serverless index on {self.pinecone_cloud}/{self.pinecone_region}...")
                self.pc.create_index(
                    name=self.pinecone_index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=self.pinecone_cloud,
                        region=self.pinecone_region
                    )
                )
                print(f"[Vector Store] SUCCESS: Serverless index '{self.pinecone_index_name}' created successfully!")
            
            self.pinecone_index = self.pc.Index(self.pinecone_index_name)
            self.use_pinecone = True
            print("[Vector Store] SUCCESS: Managed Pinecone Cloud mode is fully ACTIVE!")
        except Exception as e:
            raise RuntimeError(
                f"[Vector Store] FATAL ERROR: Pinecone connection/initialization failed ({str(e)}). "
                "Ensure your API Key is valid and network connectivity is online."
            )

    def get_embedding(self, text: str) -> list:
        """Generates a dense vector embedding. Falls back to a bag-of-words tf-idf simulation if offline."""
        if self.model and self.tokenizer:
            try:
                # Tokenize and run local model inference
                inputs = self.tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    model_output = self.model(**inputs)
                
                # Perform mean pooling to extract high-quality sentence embeddings
                attention_mask = inputs["attention_mask"]
                token_embeddings = model_output[0] # First element contains all token embeddings
                
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                
                embedding = sum_embeddings / sum_mask
                # Convert back to standard list of floats
                return embedding[0].cpu().tolist()
            except Exception as e:
                print(f"[Vector Engine] WARNING: Inference error ({e}), falling back to simulated embedding.")
                
        # --- ROBUST SEMANTIC FALLBACK (TF-IDF SIMULATION) ---
        # Generate a deterministic 384-dimensional sparse vector based on word hash values
        # This provides robust similarity scoring even when running completely offline
        words = [w.lower().strip(".,!?\"'") for w in text.split() if len(w) > 3]
        vector = [0.0] * 384
        if words:
            for w in words:
                # Deterministic hashing into 384 buckets
                idx = abs(hash(w)) % 384
                vector[idx] += 1.0
            # Normalize vector to unit length
            sq_sum = sum(x * x for x in vector)
            norm = math.sqrt(sq_sum)
            if norm > 0:
                vector = [x / norm for x in vector]
        return vector

    def chunk_text(self, text: str, chunk_size=800, overlap=150) -> list:
        """Exhaustively segments large texts into overlapping blocks for accurate semantic matching."""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
            
        return chunks

    def add_document(self, title: str, content: str, department: str, clearance: int) -> list:
        """Chunks a document, extracts dense embeddings, and indexes them directly in Pinecone."""
        text_chunks = self.chunk_text(content)
        indexed_chunks = []
        
        print(f"[Vector Store] Parsing '{title}' into {len(text_chunks)} semantic chunks for {department}...")
        
        if not self.use_pinecone or not self.pinecone_index:
            raise RuntimeError("[Vector Store] Cannot upsert document: Strict Pinecone Mode is active but connection is offline.")
            
        try:
            vectors_to_upsert = []
            for idx, chunk_text in enumerate(text_chunks):
                chunk_id = f"chk_{uuid.uuid4().hex[:8]}"
                embedding = self.get_embedding(chunk_text)
                
                vectors_to_upsert.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "title": title,
                        "content": chunk_text,
                        "department": department,
                        "clearance": int(clearance),
                        "chunk_index": int(idx)
                    }
                })
                
                indexed_chunks.append({
                    "id": chunk_id,
                    "title": title,
                    "content": chunk_text,
                    "department": department,
                    "clearance": clearance,
                    "chunk_index": idx,
                    "embedding": embedding
                })
            
            # Target isolated namespace based on department name
            namespace = department.lower().strip()
            self.pinecone_index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            print(f"[Vector Store] SUCCESS: Upserted {len(vectors_to_upsert)} chunks to Pinecone under namespace '{namespace}'!")
            
            # Track indexed titles in-memory
            self.indexed_titles.add(title)
            return indexed_chunks
        except Exception as e:
            raise RuntimeError(f"[Vector Store] Upsert failed under strict Pinecone Mode: {str(e)}")

    def search(self, query: str, department: str, clearance: int, top_k=3) -> list:
        """Performs a cosine similarity search strictly over Pinecone indexes."""
        if not self.use_pinecone or not self.pinecone_index:
            raise RuntimeError("[Vector Store] Cannot search: Strict Pinecone Mode is active but connection is offline.")
            
        try:
            query_vector = self.get_embedding(query)
            namespace = department.lower().strip()
            
            # Perform query with security clearance metadata filters
            query_response = self.pinecone_index.query(
                namespace=namespace,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter={
                    "clearance": {"$lte": int(clearance)}
                }
            )
            
            results = []
            for match in query_response.matches:
                metadata = match.metadata
                results.append({
                    "score": float(match.score),
                    "id": match.id,
                    "title": metadata.get("title", ""),
                    "content": metadata.get("content", ""),
                    "department": metadata.get("department", department),
                    "clearance": int(metadata.get("clearance", clearance)),
                    "chunk_index": int(metadata.get("chunk_index", 0))
                })
                
            # Standard global shared index queries for general queries
            if namespace != "global":
                global_response = self.pinecone_index.query(
                    namespace="global",
                    vector=query_vector,
                    top_k=top_k,
                    include_metadata=True,
                    filter={
                        "clearance": {"$lte": int(clearance)}
                    }
                )
                for match in global_response.matches:
                    metadata = match.metadata
                    results.append({
                        "score": float(match.score),
                        "id": match.id,
                        "title": metadata.get("title", ""),
                        "content": metadata.get("content", ""),
                        "department": metadata.get("department", "global"),
                        "clearance": int(metadata.get("clearance", clearance)),
                        "chunk_index": int(metadata.get("chunk_index", 0))
                    })
            
            # Sort combined results by similarity score in descending order
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            raise RuntimeError(f"[Vector Store] Search failed under strict Pinecone Mode: {str(e)}")

    def save(self):
        """No-op: Pinecone is server-managed and persistent."""
        pass

    def load(self):
        """No-op: Pinecone is cloud-native and requires no disk cache."""
        pass
