from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.rag import rag_service
from app.chat_service import process_chat_message
from app.requests_store import load_all_requests
from app.config import GROQ_MODEL, DATA_PDFS_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INICIO] Iniciando servidor FastAPI...")
    rag_service.index_documents()
    yield
    print("[CIERRE] Apagando servidor.")

app = FastAPI(
    title="Horizon Travel Group Corporate Chatbot API",
    description="Backend RAG corporativo para consultas de políticas y solicitudes de viaje con Groq",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["General"])
def read_root():
    return {
        "message": "Bienvenido a la API del Chatbot Corporativo de Horizon Travel Group",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["General"])
def health_check():
    pdf_count = len(list(DATA_PDFS_DIR.glob("*.pdf"))) if DATA_PDFS_DIR.exists() else 0
    return HealthResponse(
        status="ok",
        chunks_indexed=len(rag_service.chunks),
        model=GROQ_MODEL,
        pdf_count=pdf_count
    )

@app.post("/reindex", tags=["RAG"])
def reindex_documents():
    rag_service.index_documents()
    return {
        "status": "success",
        "message": "Documentos reindexados exitosamente",
        "chunks_indexed": len(rag_service.chunks)
    }

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat_endpoint(request: ChatRequest):
    msg = request.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
    
    result = process_chat_message(request.session_id, msg)
    return ChatResponse(
        reply=result["reply"],
        sources=result["sources"],
        request_id=result["request_id"]
    )

@app.get("/requests", tags=["Solicitudes"])
def get_requests():
    return load_all_requests()
