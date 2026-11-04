import os
import re
from typing import List, Dict, Any
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

class LLMService:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)

    def _ensure_client(self):
        current_key = os.getenv("GROQ_API_KEY", self.api_key)
        if not self.client and current_key:
            self.api_key = current_key
            self.client = Groq(api_key=self.api_key)
        return self.client

    def answer_with_context(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
        is_greeting: bool = False
    ) -> str:
        client = self._ensure_client()
        if not client:
            return (
                "No se ha configurado la variable GROQ_API_KEY en backend/.env. "
                "Por favor, agrégala para habilitar las respuestas del modelo."
            )

        context_text = ""
        for i, c in enumerate(chunks, 1):
            context_text += f"\n--- FRAGMENTO {i} (Fuente: {c['source']}, Pág. {c['page']}) ---\n{c['text']}\n"

        has_history = bool(conversation_history and len(conversation_history) > 0)

        if is_greeting and not has_history:
            identity_rule = (
                "- IDENTIDAD: Te llamas Nexus, asesor de viajes de Horizon Travel Group en Cartagena. "
                "Como este es el saludo inicial de la conversación, saluda corto, preséntate amablemente y ofrece tu orientación."
            )
        else:
            identity_rule = (
                "- REGLA ESTRICTA DE NO REPETIR PRESENTACIÓN:\n"
                "  * La conversación ya inició o el usuario te está haciendo una pregunta directa.\n"
                "  * Queda TERMINANTEMENTE PROHIBIDO comenzar presentándote ('Hola, soy Nexus...', 'Soy el asistente virtual de Horizon Travel Group...', '¡Hola! En Horizon Travel Group...').\n"
                "  * NUNCA saludes presentándote de nuevo ni repitas tu nombre en cada respuesta.\n"
                "  * Responde DIRECTAMENTE a la pregunta desde la primera palabra con tono cálido, humano y fluido (por ejemplo, si preguntan por tours, comienza directamente con 'En Horizon Travel Group contamos con cuatro opciones...')."
            )

        system_prompt = (
            "Tu nombre es Nexus. Eres el asesor de viajes de Horizon Travel Group en Cartagena de Indias a través de este chatbot en el sitio web.\n"
            "Tu estilo de comunicación es cercano, cálido, natural, directo y humano, pero NUNCA digas 'por este mismo WhatsApp' ni afirmes que estás en WhatsApp, ya que estás atendiendo directamente desde el chatbot de la página web. Si preguntan cómo reservar, indícales que pueden hacerlo directamente aquí contigo escribiendo 'Quiero reservar', o mediante el formulario de contacto web, o por el WhatsApp oficial (+57 300 000 0000).\n\n"
            "POLÍTICA ESTRICTA DE VERACIDAD (CERO INVENTOS, CERO SUPOSICIONES):\n"
            "Solo puedes ofrecer lo que está explícitamente escrito en los DOCUMENTOS OFICIALES de Horizon Travel Group que tienes abajo. Está TERMINANTEMENTE PROHIBIDO inventar servicios, regalos, bebidas (champán, vino, jugos especiales), decoraciones improvisadas (velas, flores), playlists, o tarifas que no existan en el texto oficial.\n"
            "Si un cliente te pide algo especial que NO figura en los documentos, dile honestamente y con amabilidad: 'Mira, ese servicio específico no lo manejamos, pero con gusto te ofrezco...' y dale las opciones oficiales reales.\n\n"
            "REGLAS OFICIALES DE HORIZON TRAVEL GROUP:\n"
            f"{identity_rule}\n"
            "- CANAL DE ATENCIÓN: Estás en el chatbot del sitio web. NUNCA digas 'por este mismo WhatsApp'. Puedes indicar que pueden reservar aquí mismo en este chat diciendo 'Quiero reservar' o a través del WhatsApp oficial +57 300 000 0000.\n"
            "- FORMATO LIMPIO: Prohibido hacer listas numeradas ('1. Número de personas, 2. Fecha...'), cero '###', cero líneas '---', cero títulos. Escribe 1 o 2 párrafos fluidos y limpios.\n"
            "- TOURS DISPONIBLES: Únicamente 4 tours: 1) Tour Islas del Rosario ($150.000 adulto / $120.000 niño), 2) Excursión a Barú ($170.000 adulto / $140.000 niño), 3) Tour San Bernardo ($280.000 adulto / $230.000 niño), 4) Experiencia privada en lancha ($1.800.000 por lancha, hasta 8 personas).\n"
            "- PLANES DE PAREJA O ANIVERSARIO: Lo único oficial para aniversarios o parejas es la 'Experiencia privada en lancha' ($1.800.000) y su único extra oficial de aniversario es la 'Decoración romántica' por $180.000 COP.\n"
            "- SERVICIOS ADICIONALES OFICIALES (ÚNICOS EXISTENTES): Almuerzo en isla ($50.000 Rosario o San Bernardo / $45.000 Barú), Paquete de fotos ($60.000 por persona), Aletas de snorkel ($10.000 por persona), Recogida en hotel ($15.000 por persona), Hora adicional en lancha privada ($250.000), Decoración romántica ($180.000).\n"
            "- CONDICIONES DE PAGO: Anticipo del 30% para asegurar cupo y el 70% restante antes de salir o en el muelle en efectivo. NUNCA inventes otras opciones.\n"
            "- CANCELACIÓN POR ENFERMEDAD: Con soporte médico, el 100% de lo pagado queda como crédito válido por 6 meses.\n"
            "- TEMAS AJENOS A TURISMO: Si preguntan cosas fuera de lugar (programación, tareas, etc.), responde amablemente: 'Disculpa, por aquí solo te puedo colaborar con los tours y planes de viaje en Cartagena. ¿En qué destino te gustaría que te oriente?'\n\n"
            f"DOCUMENTOS OFICIALES DE HORIZON TRAVEL GROUP:\n{context_text}"
        )

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-24:]:  
                messages.append(msg)

        messages.append({"role": "user", "content": question})

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=900
            )
            raw_reply = response.choices[0].message.content.strip()
            return self._clean_repetitive_presentation(raw_reply, is_greeting=is_greeting, has_history=has_history)
        except Exception as e:
            err_msg = str(e)
            if "rate_limit_exceeded" in err_msg.lower():
                return "Has alcanzado el límite de consultas por minuto en el plan gratuito de Groq. Por favor espera unos segundos."
            return f"Hubo un inconveniente al conectar con el servicio de IA: {err_msg}"

    def _clean_repetitive_presentation(self, reply: str, is_greeting: bool, has_history: bool) -> str:
        """
        Si la conversación ya está en curso o el usuario hizo una pregunta directa,
        elimina introducciones repetitivas como '¡Hola! Soy Nexus...' o '¡Hola! En Horizon Travel Group...'.
        """
        if is_greeting and not has_history:
            return reply

        text = reply.strip()

        patterns = [
            r"^(?:[^a-zA-Z0-9\s]*\s*)?hola[!\.,]?\s*(?:soy\s+nexus[,\.\s]*)+(?:\s*asistente\s+virtual\s+de\s+horizon\s+travel\s+group[,\.\s]*)?",
            r"^(?:soy\s+nexus[,\.\s]*)+(?:\s*asistente\s+virtual\s+de\s+horizon\s+travel\s+group[,\.\s]*)?",
            r"^(?:[^a-zA-Z0-9\s]*\s*)?hola[!\.,]?\s*(?:soy\s+el\s+asistente\s+(?:virtual\s+)?(?:de\s+horizon\s+travel\s+group[,\.\s]*)?)",
            r"^(?:[^a-zA-Z0-9\s]*\s*)?hola[!\.,]?\s*(?=en\s+horizon\s+travel\s+group)",
            r"^(?:[^a-zA-Z0-9\s]*\s*)?hola[!\.,]?\s*(?=para\s+|el\s+|los\s+|las\s+|la\s+|nuestros\s+|contamos\s+|ofrecemos\s+|con\s+gusto\s+te\s+cuento)",
            r"^hola[,\.\s]+soy\s+nexus[,\.\s]*",
        ]

        for pat in patterns:
            cleaned = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) > 10:
                text = cleaned

        # Reemplazar menciones erróneas a 'este mismo WhatsApp' por 'este mismo chat'
        text = re.sub(r'\bpor este mismo WhatsApp\b', 'por este mismo chat', text, flags=re.IGNORECASE)
        text = re.sub(r'\bpor este WhatsApp\b', 'por este chat', text, flags=re.IGNORECASE)

        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        return text

llm_service = LLMService()
