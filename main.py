import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración de credenciales desde las Variables de Entorno de Render
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN_INSTANCE = os.getenv("GREEN_API_TOKEN_INSTANCE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Cargar la guía de información desde guia.txt
GUIDE_TEXT = "Información del alojamiento no disponible."
if os.path.exists("guia.txt"):
    with open("guia.txt", "r", encoding="utf-8") as f:
        GUIDE_TEXT = f.read()

@app.route("/", methods=["GET"])
def home():
    return "Servidor del Conserje activo y 100% gratis.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("Datos recibidos del webhook:", data)

        # Verificar si el evento corresponde a un mensaje entrante de WhatsApp
        if data and data.get("typeWebhook") == "incomingMessageReceived":
            sender_data = data.get("senderData", {})
            message_data = data.get("messageData", {})
            
            chat_id = sender_data.get("chatId")
            
            text_message = ""
            if "textMessageData" in message_data:
                text_message = message_data["textMessageData"].get("textMessage", "")
            elif "extendedTextMessageData" in message_data:
                text_message = message_data["extendedTextMessageData"].get("text", "")

            if chat_id and text_message:
                print(f"Mensaje recibido de {chat_id}: {text_message}")

                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Selección automática del modelo disponible
                selected_model = "qwen/qwen3.8-27b"
                try:
                    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=groq_headers)
                    if models_resp.status_code == 200:
                        model_list = models_resp.json().get("data", [])
                        for m in model_list:
                            m_id = m.get("id", "")
                            if ("qwen" in m_id or "gpt-oss" in m_id) and "guard" not in m_id and "safeguard" not in m_id:
                                selected_model = m_id
                                break
                        print(f"Modelo de chat seleccionado: {selected_model}")
                    else:
                        print("Error al listar modelos:", models_resp.text)
                except Exception as model_err:
                    print("Excepción al consultar modelos:", model_err)

                # Definición del System Prompt optimizado para WhatsApp
                system_prompt = f"""
Eres un conserje virtual profesional, extremadamente paciente, educado y servicial para una propiedad de alquiler turístico en Skopie, Macedonia.

REGLAS ABSOLUTAS Y OBLIGATORIAS:
1. INFORMACIÓN DE LA GUÍA: Para normas, códigos, WiFi, check-in y emergencias, cíñete ESTRICTAMENTE a los datos de la guía provista.
2. CERO INVENTOS CRÍTICOS: Si un huésped pregunta algo importante sobre el funcionamiento de la casa que no está en la guía, no lo adivines; deriva amablemente al anfitrión por WhatsApp al +43 67761789024.
3. PREGUNTAS COTIDIANAS O DE SENTIDO COMÚN: Si preguntan por cosas cotidianas (dónde están los cubiertos, vasos, basura, etc.), responde guiándote por la lógica general de cualquier hogar con naturalidad y cortesía, sin inventar cajones o armarios exactos.
4. RECOMENDACIONES LOCALES (Restaurantes, farmacias, cafeterías, peluquerías, etc.):
   - Responde SIEMPRE con una lista clara de 3 a 4 opciones recomendadas en formato de viñetas (*).
   - Incluye el nombre del lugar, una breve descripción útil y su enlace directo a Google Maps.
   - NUNCA UTILICES TABLAS MARKDOWN (|---|).
5. IDIOMA: Responde SIEMPRE en el mismo idioma exacto en el que te escriba el usuario (macedonio, inglés, español, etc.). Mantén un formato limpio, conciso y optimizado para WhatsApp.

GUÍA DEL ALOJAMIENTO:
{GUIDE_TEXT}
"""

                # Petición a la API de Groq
                groq_payload = {
                    "model": selected_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": text_message
                        }
                    ],
                    "temperature": 0.7
                }
                
                ai_reply = "¡Hola! Disculpa, en este momento el servicio está temporalmente ocupado. Inténtalo de nuevo en un segundo."
                
                groq_resp = requests.post(groq_url, json=groq_payload, headers=groq_headers)
                print(f"Estado respuesta Groq: {groq_resp.status_code}")
                
                if groq_resp.status_code == 200:
                    res_json = groq_resp.json()
                    try:
                        ai_reply = res_json["choices"][0]["message"]["content"]
                    except Exception as parse_err:
                        print(f"Error parseando respuesta de Groq: {parse_err}")
                else:
                    print(f"Error detallado de Groq HTTP: {groq_resp.text}")

                # Enviar respuesta a WhatsApp mediante Green-API
                url = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
                payload = {
                    "chatId": chat_id,
                    "message": ai_reply
                }
                headers = {'Content-Type': 'application/json'}
                
                resp = requests.post(url, json=payload, headers=headers)
                print(f"Respuesta enviada a WhatsApp, estado HTTP: {resp.status_code}")

    except Exception as e:
        print(f"ERROR CRITICO EN WEBHOOK: {str(e)}")
        import traceback
        traceback.print_exc()

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
