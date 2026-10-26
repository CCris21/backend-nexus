import os
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

    def answer_with_context(self, question: str, chunks: List[Dict[str, Any]], conversation_history: List[Dict[str, str]] = None) -> str:
        client = self._ensure_client()
        if not client:
            return (
                "No se ha configurado la variable GROQ_API_KEY en backend/.env. "
                "Por favor, agrégala para habilitar las respuestas del modelo."
            )

        context_text = ""
        for i, c in enumerate(chunks, 1):
            context_text += f"\n--- FRAGMENTO {i} (Fuente: {c['source']}, Pág. {c['page']}) ---\n{c['text']}\n"

        system_prompt = (
            "Tu nombre es Nexus. Eres un asesor de viajes de Horizon Travel Group en Cartagena de Indias.\n"
            "Hablas exactamente como una persona atendiendo por WhatsApp: cercano, natural, directo y humano. NUNCA respondas como un bot, ni como una plantilla corporativa, ni como un formulario.\n\n"
            "POLÍTICA ESTRICTA DE VERACIDAD (CERO INVENTOS, CERO SUPOSICIONES):\n"
            "Solo puedes ofrecer lo que está explícitamente escrito en los DOCUMENTOS OFICIALES de Horizon Travel Group que tienes abajo. Está TERMINANTEMENTE PROHIBIDO inventar servicios, regalos, bebidas (champán, vino, jugos especiales), decoraciones improvisadas (velas, flores), playlists, o tarifas que no existan en el texto oficial.\n"
            "Si un cliente te pide algo especial que NO figura en los documentos, dile honestamente y con amabilidad: 'Mira, ese servicio específico no lo manejamos, pero con gusto te ofrezco...' y dale las opciones oficiales reales.\n\n"
            "REGLAS OFICIALES DE HORIZON TRAVEL GROUP:\n"
            "- IDENTIDAD: Te llamas Nexus. Si te saludan, saluda corto y preséntate como Nexus.\n"
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
            for msg in conversation_history[-24:]:  # Conserva los últimos 24 mensajes (12 intercambios completos)
                messages.append(msg)

        messages.append({"role": "user", "content": question})

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=900
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_msg = str(e)
            if "rate_limit_exceeded" in err_msg.lower():
                return "Has alcanzado el límite de consultas por minuto en el plan gratuito de Groq. Por favor espera unos segundos."
            return f"Hubo un inconveniente al conectar con el servicio de IA: {err_msg}"

llm_service = LLMService()
