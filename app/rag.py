import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
import numpy as np
from pypdf import PdfReader
from fastembed import TextEmbedding

from app.config import DATA_PDFS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MIN_SCORE, TOP_K

class RAGService:
    def __init__(self):
        print("[RAG] Cargando modelo de embeddings (FastEmbed - BAAI/bge-small-en-v1.5)...")
        self.embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray = np.array([])
        self.is_indexed = False

        self.index_documents()

    def extract_text_from_pdfs(self) -> List[Dict[str, Any]]:
        pages_content = []
        if not DATA_PDFS_DIR.exists():
            DATA_PDFS_DIR.mkdir(parents=True, exist_ok=True)
            return pages_content

        pdf_files = list(DATA_PDFS_DIR.glob("*.pdf"))
        print(f"[RAG] Encontrados {len(pdf_files)} PDFs en {DATA_PDFS_DIR}")

        for pdf_path in pdf_files:
            try:
                reader = PdfReader(str(pdf_path))
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_content.append({
                            "source": pdf_path.name,
                            "page": page_num,
                            "text": text.strip()
                        })
            except Exception as e:
                print(f"[RAG] Error leyendo {pdf_path.name}: {e}")

        return pages_content

    def create_chunks(self, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        for item in pages_content:
            text = item["text"]
            source = item["source"]
            page = item["page"]

            start = 0
            while start < len(text):
                end = start + CHUNK_SIZE
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "source": source,
                        "page": page
                    })
                start += (CHUNK_SIZE - CHUNK_OVERLAP)

        return chunks

    def index_documents(self):
        print("[RAG] Indexando documentos...")
        pages = self.extract_text_from_pdfs()
        if not pages:
            print("[RAG] No hay páginas con texto para indexar.")
            self.chunks = []
            self.embeddings = np.array([])
            self.is_indexed = True
            return

        self.chunks = self.create_chunks(pages)
        print(f"[RAG] Generados {len(self.chunks)} fragmentos.")

        texts = [c["text"] for c in self.chunks]

        embeddings_list = list(self.embed_model.embed(texts))
        self.embeddings = np.array(embeddings_list)
        self.is_indexed = True
        print("[RAG] ¡Indexación completada con éxito!")

    def search(self, query: str, top_k: int = TOP_K) -> Tuple[List[Dict[str, Any]], float]:

        if not self.is_indexed or len(self.chunks) == 0:
            print("[RAG] Detectado índice vacío en search(), indexando ahora mismo...")
            self.index_documents()
        
        if not self.chunks:
            return [], 0.0

        query_emb_list = list(self.embed_model.embed([query]))
        query_emb = np.array(query_emb_list[0])

        norm_query = np.linalg.norm(query_emb)
        norm_chunks = np.linalg.norm(self.embeddings, axis=1)

        scores = np.dot(self.embeddings, query_emb) / (norm_chunks * norm_query + 1e-10)

        sorted_indices = np.argsort(scores)[::-1]

        best_score = float(scores[sorted_indices[0]]) if len(sorted_indices) > 0 else 0.0

        results = []
        for idx in sorted_indices[:top_k]:
            score = float(scores[idx])
            if score >= MIN_SCORE or len(results) == 0:
                results.append({
                    "text": self.chunks[idx]["text"],
                    "source": self.chunks[idx]["source"],
                    "page": self.chunks[idx]["page"],
                    "score": round(score, 4)
                })

        return results, best_score

rag_service = RAGService()
