from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del usuario")
    session_id: str = Field(default="default_session", description="Identificador único de la sesión del usuario")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Respuesta del chatbot")
    sources: List[str] = Field(default_factory=list, description="Lista de archivos y páginas de donde proviene la información")
    request_id: Optional[str] = Field(default=None, description="Número de radicado si se completó una reserva")

class TravelRequestRecord(BaseModel):
    request_id: str
    session_id: str
    service_type: str
    destination: str
    travel_date: str
    passengers: int
    customer_name: str
    customer_email: str
    created_at: str

class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int
    model: str
    pdf_count: int
