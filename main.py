import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Configuración de credenciales desde variables de entorno
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

def cargar_guia():
    try:
        if os.path.exists("guia.txt"):
            with open("guia.txt", "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Error cargando guia.txt: {e}")
    return "No se pudo cargar la información de la guía."

GUIA_CONTENT = cargar_guia()

SYSTEM_PROMPT = f"""
Eres un conserje virtual altamente profesional, atento y paciente para un alojamiento turístico en Skopie.

INFORMACIÓN OFICIAL DEL ALOJAMIENTO (guia.txt):
{GUIA_CONTENT}

REGLAS STRICTAS DE FORMATO Y COMPORTAMIENTO:
1. IDIOMA: Responde siempre en el mismo idioma en el que te escriba el huésped (español, inglés, macedonio, etc.). Si el mensaje incluye varios idiomas, responde de forma bilingüe amable.
2. NO USAR TABLAS EN MARKDOWN. WhatsApp no las renderiza bien.
3. RECOMENDACIONES DE COMIDA / RESTAURANTES:
   - Cuando el huésped pregunte por restaurantes, dónde comer, cenar o desayunar, NUNCA le envíes la lista directa de primeras.
   - Pregúntale primero amablemente dónde se encuentra en ese momento (ejemplo: si está en el alojamiento/casa, en el centro/Plaza Macedonia o en el Antiguo Bazar).
   - Una vez que responda su ubicación, consulta 'guia.txt' y recomiéndale 2 opciones de esa zona concreta en formato de lista con viñetas (*) e incluye los enlaces a Google Maps exactos que aparecen en la guía.
4. REGLA ANTI-ALUCINACIÓN: Está prohibido inventar o recomendar lugares que no estén en guia.txt. Si te preguntan algo que no aparece en la guía o requiere intervención del dueño, facilítales con amabilidad el contacto directo del anfitrión (+43 67761789024).
5. FORMATO DE LISTAS: Cuando des recomendaciones, usa viñetas (*) con un máximo de 2-3 opciones y añade sus enlaces directos a Google Maps.
"""

def enviar_mensaje_whatsapp(chat_id, texto):
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": texto
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Respuesta de Green-API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error enviando mensaje por Green-API: {e}")

@app.route("/", methods=["GET"])
def home():
    return "Bot Conserje Virtual en ejecución.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Webhook recibido:", data)

    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    type_webhook = data.get("typeWebhook")

    if type_webhook == "incomingMessageReceived":
        message_data = data.get("messageData", {})
        sender_data = data.get("senderData", {})
        chat_id = sender_data.get("chatId")

        # Extraer texto del mensaje entrante
        text_message = ""
        if message_data.get("typeMessage") == "textMessage":
            text_message = message_data.get("textMessageData", {}).get("textMessage", "")
        elif message_data.get("typeMessage") == "extendedTextMessage":
            text_message = message_data.get("extendedTextMessageData", {}).get("text", "")

        if text_message and chat_id:
            try:
                response = groq_client.chat.completions.create(
                    model="qwen-2.5-32b",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text_message}
                    ],
                    temperature=0.3
                )
                bot_reply = response.choices[0].message.content
                enviar_mensaje_whatsapp(chat_id, bot_reply)
            except Exception as e:
                print(f"Error procesando con Groq: {e}")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
