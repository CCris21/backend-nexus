import re
import time
from typing import Dict, Any, List, Tuple
from app.rag import rag_service
from app.llm import llm_service
from app.requests_store import save_travel_request
from app.email_service import send_reservation_email
from app.config import MIN_SCORE

SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TIMEOUT_SECONDS = 1800 

def get_or_create_session(session_id: str) -> Dict[str, Any]:
    now = time.time()
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "history": [],
            "booking_state": None,
            "last_activity": now
        }
    else:
        last = SESSIONS[session_id].get("last_activity", now)
        if now - last > SESSION_TIMEOUT_SECONDS:
            SESSIONS[session_id]["booking_state"] = None
        SESSIONS[session_id]["last_activity"] = now

    return SESSIONS[session_id]

def is_greeting_intent(text: str) -> bool:
    """
    Detecta si el mensaje es un saludo inicial o comando de reinicio de la conversación.
    """
    t = re.sub(r'[^\w\s]', '', text.lower()).strip()
    greetings = [
        "hola", "hola nexus", "buenas", "buen dia", "buen día", 
        "buenos dias", "buenos días", "buenas tardes", "buenas noches", 
        "saludos", "hola buenas", "hola qué tal", "hola que tal",
        "reiniciar", "empezar de nuevo", "inicio", "empezar", "reset", "menu principal"
    ]
    return t in greetings

def is_booking_intent(text: str) -> bool:
    """
    Detecta si el usuario manifiesta explícitamente la intención de iniciar una reserva o compra de tour.
    Ignora deliberadamente preguntas informativas, dudas de políticas, porcentajes o preguntas con 'reserva'.
    """
    t = text.lower().strip()

    if "?" in t or "¿" in t:
        return False

    interrogatives = [
        "que ", "qué ", "como ", "cómo ", "cuanto ", "cuánto ", "cuanta ", "cuánta ",
        "cual ", "cuál ", "cuales ", "cuáles ", "donde ", "dónde ", "cuando ", "cuándo ",
        "por que ", "por qué ", "porcentaje ", "politica ", "política ", "requisito ", "requisitos "
    ]
    if any(t.startswith(q) for q in interrogatives):
        return False

    booking_patterns = [
        r"\b(quiero|deseo|quisiera|me gustar[ií]a|vengo a|proceder a|voy a)\s+(hacer\s+una\s+|gestionar\s+una\s+|iniciar\s+una\s+)?(reserva[rn]?|agendar|apartar)\b",
        r"\b(hacer|iniciar|comenzar|gestionar|tramitar)\s+(una\s+|la\s+)?reserva\b",
        r"\b(reservar|agendar|apartar)\s+(un|el|este|mi)?\s*(tour|viaje|paquete|lancha|cupo|salida|servicio)\b",
        r"\b(quiero|deseo|quisiera)\s+(comprar|adquirir|contratar)\s+(un|el)?\s*(tour|paquete|viaje)\b",
        r"\b(solicitar|agendar|cotizar)\s+viaje\b",
        r"^(quiero reservar|deseo reservar|iniciar reserva|hacer reserva|reservar ahora|reservar ya)$"
    ]

    return any(re.search(pat, t) for pat in booking_patterns)

def is_cancellation_intent(text: str) -> bool:
    """
    Detecta si el usuario desea cancelar el proceso de reserva en curso.
    No se activa si está preguntando por políticas de cancelación o reembolsos.
    """
    t = text.lower().strip()
    if any(q in t for q in ["?", "¿", "politica", "política", "cómo", "como", "cuándo", "cuando", "por qué", "porque"]):
        return False

    keywords = [
        "cancelar", "cancelar reserva", "detener", "salir", "ya no quiero", 
        "olvídalo", "olvidalo", "abortar", "no quiero reservar", "no deseo reservar", "parar"
    ]
    return any(k in t for k in keywords)

def is_informational_inquiry(text: str, current_step: int = 0) -> bool:
    """
    Detecta si durante un flujo de reserva el usuario está haciendo una consulta sobre
    precios, destinos, horarios, políticas, requisitos o condiciones en lugar de responder al paso.
    """
    t = text.lower().strip()

    if "?" in t or "¿" in t:
        return True

    starter_questions = [
        "que ", "qué ", "como ", "cómo ", "cuanto ", "cuánto ", "cuanta ", "cuánta ",
        "cuantos ", "cuántos ", "cuantas ", "cuántas ", "cual ", "cuál ", "cuales ", "cuáles ",
        "donde ", "dónde ", "cuando ", "cuándo ", "por que ", "por qué ", "porque ",
        "hay ", "tienen ", "tienes ", "ofrecen ", "ofrece ", "se puede ", "es posible ",
        "a que hora ", "a qué hora ", "quisiera saber ", "quiero saber ", "me gustaria saber ",
        "me gustaría saber ", "cuentame ", "cuéntame ", "explicame ", "explícame ",
        "tengo una duda ", "tengo una pregunta ", "dime ", "informacion ", "información "
    ]
    if any(t.startswith(q) for q in starter_questions):
        return True

    info_topics = [
        "porcentaje", "anticipo", "abono", "saldo", "cuanto se paga", "cuánto se paga",
        "cuanto cuesta", "cuánto cuesta", "cuanto vale", "cuánto vale", "precio", "precios",
        "tarifa", "tarifas", "costo", "costos", "descuento", "descuentos",
        "reembolso", "devolucion", "devolución", "cancelacion", "cancelación", "reprogramar",
        "medio de pago", "medios de pago", "forma de pago", "formas de pago", "tarjeta",
        "dolares", "dólares", "nequi", "daviplata", "efectivo", "factura",
        "punto de encuentro", "muelle", "bodeguita", "recogida", "transporte",
        "almuerzo", "comida", "vegetariano", "bebida", "bebidas", "alcohol",
        "niño", "niños", "edad", "bebe", "bebés", "embaraz", "nadar", "snorkeling", "chaleco", "mascota", "mascotas",
        "parque nacional", "entrada al parque", "ingreso al parque", "mal clima", "lluvia",
        "que incluye", "qué incluye", "duracion", "duración", "horario", "horarios"
    ]
    if any(topic in t for topic in info_topics):
        return True

    if current_step == 5:
        words = t.split()
        if len(words) > 4:
            return True
        if any(w in t for w in ["puedo", "debo", "pagar", "saber", "costar", "incluye", "tienen", "vale"]):
            return True

    return False

def get_booking_step_prompt(step: int, data: Dict[str, Any]) -> str:
    """
    Retorna el recordatorio del dato pendiente para continuar con la reserva en curso.
    """
    if step == 1:
        return "*(Para continuar con tu solicitud de reserva: ¿qué tipo de servicio te gustaría reservar? Ej: Paquete turístico, Vuelo, Hotel o Transporte)*"
    elif step == 2:
        return f"*(Para continuar con tu solicitud de reserva de {data.get('service_type', 'tu viaje')}: ¿cuál es la ciudad o lugar de destino?)*"
    elif step == 3:
        return f"*(Para continuar con tu reserva a {data.get('destination', 'tu destino')}: ¿en qué fecha estimada deseas viajar?)*"
    elif step == 4:
        return "*(Para continuar con tu reserva: ¿para cuántas personas sería?)*"
    elif step == 5:
        return "*(Para continuar con tu reserva: ¿a nombre de quién la registramos? Por favor indícanos tu nombre y apellido completos en una sola línea)*"
    elif step == 6:
        return f"*(Para continuar con tu reserva a nombre de {data.get('customer_name', '')}: ¿nos indicas un número de teléfono o WhatsApp de contacto?)*"
    elif step == 7:
        return "*(Por último, para finalizar tu reserva: ¿nos facilitas un correo electrónico para enviarte la confirmación?)*"
    return "*(¿Deseas continuar con tu solicitud de reserva?)*"

def validate_full_name(text: str) -> Tuple[bool, str]:
    cleaned = text.strip()
    if re.search(r'\d', cleaned):
        return False, "El nombre no debe contener números. Por favor escribe tu nombre y apellido reales en una sola línea (ejemplo: Carlos Crismatt):"
    
    if re.search(r'[<>/{}\[\]\\=@#$%^&*~_]', cleaned):
        return False, "Por favor evita símbolos o caracteres especiales. Escribe tu nombre y apellido completos en una sola línea:"

    words = [w for w in cleaned.split() if len(w) > 1]
    if len(words) < 2:
        return False, "Por favor ingresa tu nombre completo (al menos un nombre y un apellido en una sola línea, ej: Carlos Crismatt):"

    if len(cleaned) < 5 or len(cleaned) > 80:
        return False, "El nombre ingresado parece muy corto o inválido. Por favor escribe tu nombre y apellido completos:"

    return True, cleaned

def validate_phone_number(text: str) -> Tuple[bool, str]:
    cleaned = text.strip()
    digits = re.sub(r'[\s\-\(\)\+]', '', cleaned)
    
    if re.search(r'[a-zA-Z]', cleaned):
        return False, "El teléfono no debe contener letras. Por favor escribe un número válido (ejemplo: 3001234567 o +57 300 123 4567):"
    
    if not digits.isdigit():
        return False, "Ese número tiene caracteres extraños. Por favor escribe un número de teléfono o celular válido:"
        
    if len(digits) < 10 or len(digits) > 15:
        return False, "Ese número parece incompleto o extraño. Por favor escribe un número válido con al menos 10 dígitos (ej: 3001234567):"
    
    if len(set(digits)) == 1:
        return False, "Ese número de teléfono no parece real (todos los dígitos son iguales). Por favor escribe tu número de contacto real:"
        
    if digits in "0123456789012345":
        return False, "Ese número parece una secuencia de prueba. Por favor escribe un número de teléfono real:"

    return True, cleaned

def handle_booking_flow(session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    state = session["booking_state"]
    step = state.get("step", 1)
    data = state.get("data", {})

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
            "reply": "Anotado. ¿A nombre de quién registramos la solicitud? Por favor escribe tu nombre y apellido completos en una sola línea (ej: Carlos Crismatt):",
            "sources": [],
            "request_id": None
        }

    elif step == 5:
        is_valid, result_name = validate_full_name(user_message)
        if not is_valid:
            return {
                "reply": result_name,
                "sources": [],
                "request_id": None
            }
        
        data["customer_name"] = result_name
        state["step"] = 6
        return {
            "reply": f"Mucho gusto, {result_name}. Ahora por favor indícanos tu número de teléfono o WhatsApp de contacto:",
            "sources": [],
            "request_id": None
        }

    elif step == 6:
        is_valid, result_phone = validate_phone_number(user_message)
        if not is_valid:
            return {
                "reply": result_phone,
                "sources": [],
                "request_id": None
            }

        data["customer_phone"] = result_phone
        state["step"] = 7
        return {
            "reply": "Excelente. Por último, facilítanos un correo electrónico de contacto para enviarte la confirmación y los detalles:",
            "sources": [],
            "request_id": None
        }

    elif step == 7:
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
        send_reservation_email(data, req_id)
        session["booking_state"] = None  

        summary_reply = (
            f"🎉 ¡Tu solicitud ha sido registrada exitosamente!\n\n"
            f"📌 **Número de Radicado:** `{req_id}`\n"
            f"• **Servicio:** {data['service_type']}\n"
            f"• **Destino:** {data['destination']}\n"
            f"• **Fecha:** {data['travel_date']}\n"
            f"• **Viajeros:** {data['passengers']}\n"
            f"• **Titular:** {data['customer_name']}\n"
            f"• **Teléfono:** {data['customer_phone']}\n"
            f"• **Correo:** {data['customer_email']}\n\n"
            f"Hemos recibido tu información y se ha notificado a nuestro equipo. Un asesor se pondrá en contacto contigo a la brevedad. ¿Deseas consultar algo más?"
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
    msg_clean = message.strip()

    if is_greeting_intent(msg_clean):
        session["booking_state"] = None
        has_history = bool(session["history"])
        
        if not has_history:
            reply = "¡Hola! Soy Nexus, asesor de viajes de Horizon Travel Group en Cartagena. ¿En qué puedo colaborarte hoy?"
        else:
            reply = "¡Hola de nuevo! ¿En qué más te puedo colaborar hoy respecto a tus planes o consultas de viaje?"

        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "sources": [],
            "request_id": None
        }

    if session["booking_state"] is not None and is_cancellation_intent(msg_clean):
        session["booking_state"] = None
        reply = "Entendido, he cancelado el proceso de solicitud de reserva. ¿En qué más te puedo colaborar hoy?"
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "sources": [],
            "request_id": None
        }

    if session["booking_state"] is not None:
        current_step = session["booking_state"].get("step", 1)
        
        if is_informational_inquiry(msg_clean, current_step=current_step):
            chunks, _ = rag_service.search(msg_clean)
            if not chunks and session["history"]:
                chunks, _ = rag_service.search(f"{msg_clean} Horizon Travel Group")

            sources = list(dict.fromkeys([f"{c['source']} (Pág. {c['page']})" for c in chunks])) if chunks else []

            if chunks:
                answer = llm_service.answer_with_context(
                    question=msg_clean,
                    chunks=chunks,
                    conversation_history=session["history"],
                    is_greeting=False
                )
            else:
                answer = (
                    "No encontré ese detalle específico en los documentos oficiales. "
                    "Te recuerdo que puedes consultar directamente con un asesor por WhatsApp al +57 300 000 0000."
                )

            continuation_hint = get_booking_step_prompt(current_step, session["booking_state"].get("data", {}))
            full_reply = f"{answer}\n\n{continuation_hint}"

            session["history"].append({"role": "user", "content": message})
            session["history"].append({"role": "assistant", "content": full_reply})
            return {
                "reply": full_reply,
                "sources": sources,
                "request_id": None
            }

        result = handle_booking_flow(session, msg_clean)
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": result["reply"]})
        return result

    if is_booking_intent(msg_clean):
        session["booking_state"] = {
            "step": 1,
            "data": {}
        }
        reply = (
            "¡Con gusto te ayudo a gestionar tu solicitud de viaje! "
            "Para comenzar, ¿qué tipo de servicio te gustaría reservar? (Por ejemplo: Paquete turístico, Vuelo, Hotel o Transporte)."
        )
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "sources": [],
            "request_id": None
        }

    chunks, best_score = rag_service.search(msg_clean)
    
    if not chunks and session["history"]:
        last_user_msgs = [m["content"] for m in session["history"] if m["role"] == "user"]
        if last_user_msgs:
            chunks, best_score = rag_service.search(f"{last_user_msgs[-1]} {msg_clean}")

    if not chunks:
        reply = (
            "No encontré esa información en los documentos oficiales de la empresa. "
            "Por favor comunícate con un asesor para más detalles al WhatsApp +57 300 000 0000 o al correo hola@horizontravelgroup.com."
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
        question=msg_clean,
        chunks=chunks,
        conversation_history=session["history"],
        is_greeting=False
    )

    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "sources": sources,
        "request_id": None
    }
