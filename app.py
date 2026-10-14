import os
import json
import traceback
from flask import Flask, request, render_template
import requests
from openai import OpenAI

app = Flask(__name__)

# Memoria temporal de chat por usuario para mantener el contexto y la ubicación
chat_histories = {}

def get_property_config(property_name="skopie"):
    try:
        with open(f"properties/{property_name}/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"nombre": "Alojamiento"}

def get_property_guide(property_name="skopie"):
    try:
        with open(f"properties/{property_name}/guia.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Guía no disponible."

@app.route("/")
def home():
    config = get_property_config("skopie")
    return render_template("index.html", config=config)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        if data.get("typeWebhook") == "incomingMessageReceived":
            message_data = data.get("messageData", {})
            if message_data.get("typeMessage") == "textMessage":
                text = message_data.get("textMessageData", {}).get("textMessage", "")
                sender = data.get("senderData", {}).get("chatId", "")
                
                if sender and text:
                    response_text = ask_groq(sender, text, "skopie")
                    send_whatsapp_message(sender, response_text)
    except Exception as e:
        print("--- ERROR EN WEBHOOK ---")
        traceback.print_exc()
    return "OK", 200

def ask_groq(sender, user_message, property_name):
    client = OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    guide = get_property_guide(property_name)
    
    # Inicializar historial del usuario si no existe
    if sender not in chat_histories:
        chat_histories[sender] = []
    
    # Guardar mensaje del usuario en la memoria
    chat_histories[sender].append({"role": "user", "content": user_message})
    
    # Mantener solo los últimos 6 mensajes para no sobrecargar
    if len(chat_histories[sender]) > 6:
        chat_histories[sender] = chat_histories[sender][-6:]
    
    system_prompt = f"""
    Eres un conserje virtual experto, amable y de categoría mundial para un apartamento turístico. No eres un contestador automático rígido; eres un conserje local profesional que conoce a la perfección la ciudad, sus mejores restaurantes, cafés, zonas de ambiente y atracciones.

    INSTRUCCIONES CLAVE DE COMPORTAMIENTO:
    1. ROL DE CONSERJE LOCAL: Si el huésped te pide recomendaciones (dónde cenar, qué visitar, dónde ir en una zona concreta como Kisela Voda o el centro), utiliza tu conocimiento experto para recomendarle excelentes lugares reales de la ciudad. Aporta valor, describe brevemente las opciones y actúa como un guía profesional.
    2. MAPAS FUNCIONALES AUTOMÁTICOS: Para cualquier lugar que recomiendes, añade siempre un enlace de búsqueda de Google Maps funcional y directo usando este formato exacto: `https://www.google.com/maps/search/?api=1&query=Nombre+Del+Lugar+Ciudad` para que el huésped pueda abrirlo con un solo toque en WhatsApp.
    3. INFORMACIÓN DEL APARTAMENTO: Utiliza la guía oficial que se muestra más abajo exclusivamente para los detalles internos del alojamiento (normas de la casa, WiFi, llaves, códigos, etc.).
    4. IDIOMA Y MEMORIA: Responde siempre en el mismo idioma en el que te escriba el huésped en su último mensaje y mantén el hilo de la conversación previa.
    5. FORMATO LIMPIO: Escribe de forma natural, clara y cercana para WhatsApp, sin utilizar símbolos de encabezado en Markdown como '###'.

    Aquí tienes la guía de referencia del alojamiento:
    {guide}
    """
    
    messages = [{"role": "system", "content": system_prompt}] + chat_histories[sender]
    
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        temperature=0.3,  # Subimos ligeramente la temperatura para que sea más natural y creativo recomendando
        max_tokens=600
    )
    
    bot_reply = completion.choices[0].message.content
    
    # Guardar la respuesta del bot en la memoria
    chat_histories[sender].append({"role": "assistant", "content": bot_reply})
    
    return bot_reply

def send_whatsapp_message(chat_id, message):
    instance_id = os.environ.get("GREEN_API_INSTANCE_ID")
    token = os.environ.get("GREEN_API_TOKEN")
    url = f"https://api.green-api.com/waInstance{instance_id}/sendMessage/{token}"
    payload = {
        "chatId": chat_id,
        "message": message
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
