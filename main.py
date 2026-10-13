import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configurar Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Configurar Green-API
GREEN_API_ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
GREEN_API_TOKEN_INSTANCE = os.environ.get("GREEN_API_TOKEN_INSTANCE")
GREEN_API_URL = os.environ.get("GREEN_API_URL")

# Cargar la guía si existe
GUIA_PATH = "guia.txt"
contexto_guia = ""
if os.path.exists(GUIA_PATH):
    with open(GUIA_PATH, "r", encoding="utf-8") as f:
        contexto_guia = f.read()

@app.route("/", methods=["GET"])
def home():
    return "¡El Bot del Conserje de la Costa Blanca con Green-API y Gemini está activo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    
    try:
        # Verificar si es un mensaje entrante de WhatsApp
        if data.get("typeWebhook") == "incomingMessageReceived":
            sender_data = data.get("senderData", {})
            message_data = data.get("messageData", {})
            
            # Obtener el teléfono del remitente
            chat_id = sender_data.get("chatId") # Formato: 346XXXXXXXX@c.us
            
            # Extraer el texto del mensaje (soporta texto plano o extendido)
            text_message = ""
            if "textMessageData" in message_data:
                text_message = message_data["textMessageData"].get("textMessage", "")
            elif "extendedTextMessageData" in message_data:
                text_message = message_data["extendedTextMessageData"].get("text", "")
                
            if text_message and chat_id:
                # Construir el prompt para Gemini con la guía de contexto
                prompt = f"""
                Eres un asistente virtual / conserje amable y servicial para un alojamiento en la Costa Blanca.
                Usa la siguiente información de la guía para responder a las dudas del huésped de forma natural y cercana:
                ---
                {contexto_guia}
                ---
                Pregunta del huésped: {text_message}
                """
                
                # Generar respuesta con Gemini
                response = model.generate_content(prompt)
                ai_reply = response.text
                
                # Enviar respuesta de vuelta por WhatsApp usando Green-API
                send_url = f"{GREEN_API_URL}/waInstance{GREEN_API_ID_INSTANCE}/sendMessage/{GREEN_API_TOKEN_INSTANCE}"
                payload = {
                    "chatId": chat_id,
                    "message": ai_reply
                }
                requests.post(send_url, json=payload)

    except Exception as e:
        print(f"Error procesando el webhook: {e}")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
