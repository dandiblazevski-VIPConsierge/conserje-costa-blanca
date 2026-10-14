# Conserje Virtual - Skopie Apartment

Bot de atención automática para huéspedes vía WhatsApp integrado con Groq AI y Green-API.

## Estructura Modular
- `app.py`: Servidor principal y lógica del bot de WhatsApp.
- `properties/skopie/`: Configuración (`config.json`) y guía del alojamiento (`guia.txt`).
- `templates/index.html`: Pantalla de estado del servicio web.

## Configuración en Render
Comando de inicio (Start Command):
`gunicorn app:app`

Variables de entorno necesarias:
- `GROQ_API_KEY`
- `GREEN_API_INSTANCE_ID`
- `GREEN_API_TOKEN`
