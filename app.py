import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from groq import Groq

app = Flask(__name__)

# Configuración de credenciales desde variables de entorno
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

def cargar_propiedad(nombre_propiedad="skopie"):
    """Carga la configuración y la guía específica de la propiedad de forma modular."""
    base_path = os.path.join("properties", nombre_propiedad)
    
    config = {}
    config_path = os.path.join(base_path, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error cargando config.json: {e}")
            
    guia_content = "No se pudo cargar la información de la guía."
    guia_path = os.path.join(base_path, "guia.txt")
    if os.path.exists(guia_path):
        try:
            with open(guia_path, "r", encoding="utf-8") as f:
                guia_content = f.read()
        except Exception as e:
            print(f"Error cargando guia.txt: {e}")
            
    return config, guia_content

# Cargamos por defecto la propiedad de Skopie
CONFIG, GUIA_CONTENT = cargar_propiedad("skopie")

def obtener_modelo_activo():
    """Obtiene dinámicamente un modelo de chat válido, excluyendo guards y embeddings."""
    try:
        modelos_response = groq_client.models.list()
        modelos_disponibles = [m.id for m in modelos_response.data]
        
        # Buscar preferiblemente modelos de chat estables
        for prefijo in ["llama-3.3-70b", "llama3-70b", "llama-3.1-8b", "llama3-8b", "llama-3", "qwen", "gemma2", "mistral"]:
            for m_id in modelos_disponibles:
                if prefijo in m_id and "guard" not in m_id and "embed" not in m_id and "whisper" not in m_id:
                    print(f"Modelo de chat seleccionado: {m_id}")
                    return m_id
        
        # Buscar cualquier otro modelo de chat válido
        for m_id in modelos_disponibles:
            if "guard" not in m_id and "embed" not in m_id and "whisper" not in m_id:
                print(f"Usando modelo alternativo válido: {m_id}")
                return m_id
    except Exception as e:
        print(f"Error consultando modelos activos: {e}")
    
    return "llama-3.1-8b-instant"

SYSTEM_PROMPT = f"""
Eres un conserje virtual altamente profesional, atento y paciente para el alojamiento turístico: {CONFIG.get('nombre', 'Alojamiento')} ubicado en {CONFIG.get('ubicacion', 'Skopie')}.

INFORMACIÓN OFICIAL DEL ALOJAMIENTO (guia.txt):
{GUIA_CONTENT}

REGLAS ESTRICTAS DE FORMATO Y COMPORTAMIENTO:
1. IDIOMA: Responde siempre en el mismo idioma en el que te escriba el huésped (español, inglés, macedonio, etc.).
2. NO USAR TABLAS EN MARKDOWN. WhatsApp no las renderiza bien.
3. RECOMENDACIONES DE COMIDA / RESTAURANTES:
   - Cuando el huésped pregunte por restaurantes, dónde comer, cenar o desayunar, NUNCA le envíes la lista directa de primeras.
   - Pregúntale primero amablemente dónde se encuentra en ese momento (ejemplo: si está en el alojamiento/casa, en el centro o en el bazar).
   - Una vez que responda su ubicación, consulta 'guia.txt' y recomiéndale 2 opciones de esa zona concreta en formato de lista con viñetas (*) e incluye los enlaces a Google Maps exactos que aparecen en la guía.
4. REGLA ANTI-ALUCINACIÓN: Está prohibido inventar o recomendar lugares que no estén en guia.txt. Si te preguntan algo que no aparece en la guía o requiere intervención del dueño, facilítales con amabilidad el contacto directo del anfitrión ({CONFIG.get('contacto_anfitrion', '+43 67761789024')}).
5. FORMATO DE LISTAS: Cuando des recomendaciones, usa viñetas (*) con un máximo de 2-3 opciones y añade sus enlaces directos a Google Maps.
"""

def enviar_mensaje_whatsapp(chat_id, texto):
    url = f"https://7107.api.greenapi.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
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
    return render_template("index.html", config=CONFIG)

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

        text_message = ""
        if message_data.get("typeMessage") == "textMessage":
            text_message = message_data.get("textMessageData", {}).get("textMessage", "")
        elif message_data.get("typeMessage") == "extendedTextMessage":
            text_message = message_data.get("extendedTextMessageData", {}).get("text", "")

        if text_message and chat_id:
            try:
                modelo_a_usar = obtener_modelo_activo()
                response = groq_client.chat.completions.create(
                    model=modelo_a_usar,
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
