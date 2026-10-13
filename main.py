import os
from flask import Flask, request, jsonify
from whatsapp_api_client_python import GreenAPI
import google.generativeai as genai

app = Flask(__name__)

# Configuración de credenciales desde las Variables de Entorno de Render
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN_INSTANCE = os.getenv("GREEN_API_TOKEN_INSTANCE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializar Green-API y Gemini
green_api = GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE)
genai.configure(api_key=GEMINI_API_KEY)

# Configuración del modelo Gemini (con un System Prompt de Conserje)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

system_instruction = (
    "Eres un conserje virtual amable y eficiente para alojamientos turísticos en la Costa Blanca. "
    "Respondes de forma clara, educada y servicial basándote en la información disponible."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=system_instruction
)

# Cargar la guía de información si existe
GUIDE_TEXT = "Bienvenido a tu alojamiento en la Costa Blanca."
if os.path.exists("guia.txt"):
    with open("guia.txt", "r", encoding="utf-8") as f:
        GUIDE_TEXT = f.read()

@app.route("/", methods=["GET"])
def home():
    return "El servidor del Bot Conserje de WhatsApp está activo y funcionando correctamente.", 200

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
            
            # Extraer el texto del mensaje (soporta texto plano o extendido)
            text_message = ""
            if "textMessageData" in message_data:
                text_message = message_data["textMessageData"].get("textMessage", "")
            elif "extendedTextMessageData" in message_data:
                text_message = message_data["extendedTextMessageData"].get("text", "")

            if chat_id and text_message:
                print(f"Mensaje recibido de {chat_id}: {text_message}")

                # Crear el prompt combinando la guía y la pregunta del huésped
                prompt = f"""
                Información de la guía del alojamiento:
                {GUIDE_TEXT}

                Pregunta del huésped:
                {text_message}

                Responde de manera natural, servicial y directa al huésped basándote en la guía.
                """

                # Generar respuesta con Gemini
                response = model.generate_content(prompt)
                ai_reply = response.text

                # Enviar respuesta de vuelta a WhatsApp usando Green-API
                green_api.sending.sendMessage(chat_id, ai_reply)
                print(f"Respuesta enviada a {chat_id}")

    except Exception as e:
        print(f"ERROR CRITICO EN WEBHOOK: {str(e)}")
        import traceback
        traceback.print_exc()

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
