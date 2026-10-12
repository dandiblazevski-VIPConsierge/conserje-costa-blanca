import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configuración de credenciales desde las variables de entorno de Render
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto_123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configurar Google Gemini con instrucciones de sistema profesionales
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 800,
    }
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        system_instruction=(
            "Eres un conserje digital de lujo altamente profesional para propiedades vacacionales exclusivas en la Costa Blanca (España). "
            "Tu tono es siempre cálido, elegante, conciso y orientado a la excelencia en el servicio al cliente. "
            "Respondes a los huéspedes por WhatsApp ayudándoles con información sobre la zona, recomendaciones locales, "
            "servicios de traslado y dudas generales sobre su estancia."
        ),
    )

@app.route("/", methods=["GET"])
def home():
    """Ruta raíz para comprobar el estado vital del servidor."""
    return "Conserje Costa Blanca - Bot de WhatsApp Activo y Operativo", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Verificación del Webhook requerida por la API de Meta."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("Webhook verificado exitosamente por Meta.")
            return challenge, 200
        else:
            return "Token de verificación inválido", 403
    return "Parámetros de solicitud inválidos", 400

@app.route("/webhook", methods=["POST"])
def webhook():
    """Recepción, validación y procesamiento de mensajes entrantes de WhatsApp."""
    try:
        body = request.get_json()
        
        # Validar la estructura de datos proveniente de Meta
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages")
                    
                    if messages:
                        message = messages[0]
                        from_number = message.get("from")  # Número de teléfono del huésped
                        msg_body = message.get("text", {}).get("body")
                        
                        if msg_body:
                            print(f"Mensaje recibido de {from_number}: {msg_body}")
                            
                            # Generar respuesta inteligente mediante Gemini
                            response_text = generate_gemini_response(msg_body)
                            
                            # Enviar respuesta de vuelta al chat de WhatsApp
                            send_whatsapp_message(from_number, response_text)
                            
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error crítico procesando el webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_gemini_response(user_message):
    """Genera una respuesta contextual utilizando el modelo de Google Gemini."""
    try:
        if not GEMINI_API_KEY:
            return "Disculpa, el servicio de asistencia inteligente no se encuentra configurado en este momento."
        
        chat_response = model.generate_content(user_message)
        return chat_response.text
    except Exception as e:
        print(f"Error en la API de Gemini: {str(e)}")
        return "Disculpa, he experimentado un pequeño inconveniente técnico procesando tu mensaje. En un momento te atiende nuestro equipo humano."

def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de texto formateado a través de la API Cloud de Meta WhatsApp."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Faltan credenciales de WhatsApp configuradas en el entorno.")
        return

    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text},
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error al enviar mensaje a WhatsApp: {response.text}")
    else:
        print(f"Mensaje respondido con éxito a {to_number}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
