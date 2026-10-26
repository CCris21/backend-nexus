import re
from typing import Dict, Any, List
from app.rag import rag_service
from app.llm import llm_service
from app.requests_store import save_travel_request
from app.config import MIN_SCORE

SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_or_create_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "history": [],
            "booking_state": None  
        }
    return SESSIONS[session_id]

def is_booking_intent(text: str) -> bool:
    keywords = ["reservar", "reserva", "solicitar viaje", "cotizar viaje", "agendar viaje", "comprar paquete", "hacer una reserva"]
    t = text.lower()
    return any(k in t for k in keywords)

def is_cancellation_intent(text: str) -> bool:
    keywords = ["cancelar", "detener", "salir", "ya no quiero", "olvídalo", "abortar"]
    t = text.lower()
    return any(k in t for k in keywords)

def handle_booking_flow(session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    state = session["booking_state"]
    step = state.get("step", 1)
    data = state.get("data", {})

    if is_cancellation_intent(user_message):
        session["booking_state"] = None
        return {
            "reply": "Entendido, he cancelado el proceso de solicitud. ¿En qué más te puedo ayudar?",
            "sources": [],
            "request_id": None
        }

    if step == 1:
        data["service_type"] = user_message.strip()
        state["step"] = 2
        return {
            "reply": "Excelente. ¿Cuál es la ciudad o lugar de destino?",
            "sources": [],
            "request_id": None
        }

    elif step == 2:
        data["destination"] = user_message.strip()
        state["step"] = 3
        return {
            "reply": "Perfecto. ¿En qué fecha estimada deseas viajar? (Ej: 15 de Noviembre o 2026-11-15)",
            "sources": [],
            "request_id": None
        }

    elif step == 3:
        data["travel_date"] = user_message.strip()
        state["step"] = 4
        return {
            "reply": "¿Para cuántas personas sería la reserva?",
            "sources": [],
            "request_id": None
        }

    elif step == 4:
        numbers = re.findall(r'\d+', user_message)
        if not numbers or int(numbers[0]) <= 0:
            return {
                "reply": "Por favor indica un número válido de personas (ejemplo: 2 o 4 personas).",
                "sources": [],
                "request_id": None
            }
        data["passengers"] = int(numbers[0])
        state["step"] = 5
        return {
            "reply": "Anotado. ¿A nombre de quién registramos la solicitud? (Nombre y apellido)",
            "sources": [],
            "request_id": None
        }

    elif step == 5:
        data["customer_name"] = user_message.strip()
        state["step"] = 6
        return {
            "reply": "Por último, facilítanos un correo electrónico de contacto para enviarte la confirmación.",
            "sources": [],
            "request_id": None
        }

    elif step == 6:
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        match = re.search(email_pattern, user_message)
        if not match:
            return {
                "reply": "El correo ingresado no parece válido. Por favor escribe un correo válido (ej: nombre@correo.com):",
                "sources": [],
                "request_id": None
            }

        data["customer_email"] = match.group(0)
        
        req_id = save_travel_request(session.get("session_id", "default"), data)
        session["booking_state"] = None  

        summary_reply = (
            f"🎉 ¡Tu solicitud ha sido registrada exitosamente!\n\n"
            f"📌 **Número de Radicado:** `{req_id}`\n"
            f"• **Servicio:** {data['service_type']}\n"
            f"• **Destino:** {data['destination']}\n"
            f"• **Fecha:** {data['travel_date']}\n"
            f"• **Viajeros:** {data['passengers']}\n"
            f"• **Titular:** {data['customer_name']}\n"
            f"• **Correo:** {data['customer_email']}\n\n"
            f"Un asesor de nuestro equipo se pondrá en contacto contigo a la brevedad. ¿Deseas consultar algo más?"
        )

        return {
            "reply": summary_reply,
            "sources": [],
            "request_id": req_id
        }

    return {
        "reply": "¿En qué puedo colaborarte hoy?",
        "sources": [],
        "request_id": None
    }


def process_chat_message(session_id: str, message: str) -> Dict[str, Any]:
    session = get_or_create_session(session_id)
    session["session_id"] = session_id

    if session["booking_state"] is not None:
        result = handle_booking_flow(session, message)
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": result["reply"]})
        return result

    if is_booking_intent(message):
        session["booking_state"] = {
            "step": 1,
            "data": {}
        }
        reply = (
            "¡Con gusto te ayudo a gestionar tu solicitud de viaje! "
            "Para comenzar, ¿qué tipo de servicio requieres? (Por ejemplo: Paquete turístico, Vuelo, Hotel o Transporte)."
        )
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "sources": [],
            "request_id": None
        }

    search_query = message
    if session["history"]:
        last_user_msgs = [m["content"] for m in session["history"] if m["role"] == "user"]
        if last_user_msgs:
            search_query = f"{last_user_msgs[-1]} {message}"

    chunks, best_score = rag_service.search(search_query)
    
    if not chunks:
        chunks, best_score = rag_service.search(message)

    if not chunks:
        reply = (
            "No encontré esa información en los documentos oficiales de la empresa. "
            "Por favor comunícate con un asesor para más detalles."
        )
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "sources": [],
            "request_id": None
        }

    sources = list(dict.fromkeys([f"{c['source']} (Pág. {c['page']})" for c in chunks]))

    reply = llm_service.answer_with_context(
        question=message,
        chunks=chunks,
        conversation_history=session["history"]
    )

    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "sources": sources,
        "request_id": None
    }
