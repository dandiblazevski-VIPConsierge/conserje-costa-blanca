import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Configuración de variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto_123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Cargar la guía local
def cargar_guia():
    try:
        with open("guia.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Guía general de la Costa Blanca disponible para atender al huésped."

# Inicializar cliente de Gemini
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

@app.route("/", methods=["GET"])
def home():
    return "Servidor del Conserje Digital activo."

# Webhook para verificación de Meta/WhatsApp
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token de verificación inválido", 403

# Webhook para recibir y responder mensajes de WhatsApp
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            
            if message.get("type") == "text":
                user_text = message["text"]["body"]
                
                # Generar respuesta con Gemini
                guia_contexto = cargar_guia()
                system_prompt = (
                    "Eres el Conserje Digital VIP de propiedades en la Costa Blanca. "
                    "Atiendes a los huéspedes de forma elegante, proactiva y cercana. "
                    "Usa la siguiente guía para responder a sus dudas sobre la zona y servicios:\n\n"
                    f"{guia_contexto}"
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_text,
                    config={'system_instruction': system_prompt}
                )
                
                reply_text = response.text if response else "Disculpe, no he podido procesar su solicitud en este momento."
                
                # Enviar respuesta por WhatsApp API
                send_whatsapp_message(from_number, reply_text)
                
    except Exception as e:
        print(f"Error procesando el mensaje: {e}")
        
    return jsonify({"status": "success"}), 200

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
