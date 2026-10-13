import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración de credenciales de Green-API y Groq desde las Variables de Entorno de Render
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN_INSTANCE = os.getenv("GREEN_API_TOKEN_INSTANCE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Cargar la guía de información si existe
GUIDE_TEXT = "Bienvenido a tu alojamiento en la Costa Blanca."
if os.path.exists("guia.txt"):
    with open("guia.txt", "r", encoding="utf-8") as f:
        GUIDE_TEXT = f.read()

@app.route("/", methods=["GET"])
def home():
    return "El servidor del Bot Conserje de WhatsApp con Groq está activo y funcionando correctamente.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("Datos recibidos del webhook:", data)

        # Verificar si el evento corresponde a un mensaje entrante
        if data and data.get("typeWebhook") == "incomingMessageReceived":
            sender_data = data.get("senderData", {})
            message_data = data.get("messageData", {})
            
            # Obtener el chat ID (remitente)
            chat_id = sender_data.get("chatId")
            
            # Extraer el texto del mensaje
            text_message = ""
            if "textMessageData" in message_data:
                text_message = message_data["textMessageData"].get("textMessage", "")
            elif "extendedTextMessageData" in message_data:
                text_message = message_data["extendedTextMessageData"].get("text", "")

            if chat_id and text_message:
                print(f"Mensaje recibido de {chat_id}: {text_message}")

                # Llamada HTTP directa a la API de Groq (Llama 3)
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                groq_payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Eres un conserje virtual amable y eficiente para alojamientos turísticos en la Costa Blanca. Respondes de forma clara, educada y servicial basándote en la siguiente información de la guía del alojamiento:\n\n{GUIDE_TEXT}"
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

                # Enviar respuesta de vuelta a WhatsApp usando la API HTTP de Green-API
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
