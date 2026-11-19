import time
import streamlit as st
from ultralytics import YOLO 
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

# Configuración de la interfaz web
st.set_page_config(page_title="EcoOrden - Asistente de Reconocimiento", page_icon="♻️", layout="centered")

st.title("♻️ EcoOrden: Clasificador Inteligente de Residuos")
st.write("Sube una foto 📥 o usa tu cámara 📷 para identificar el residuo y enviar la orden inmediata al contenedor físico (Wokwi).")

# Cargar el modelo YOLOv8 liviano (se descarga de forma automática la primera vez)
@st.cache_resource
def load_model():
    return YOLO('yolov8n.pt')

with st.spinner("Cargando modelo de visión artificial..."):
    model = load_model()

# Seleccionar método de entrada (Cumple con la interfaz de Visión)
opcion = st.radio("Selecciona el método de entrada:", ("Subir imagen", "Usar cámara"))

imagen_cargada = None
if opcion == "Subir imagen":
    imagen_cargada = st.file_uploader("Elige una foto del residuo...", type=["jpg", "jpeg", "png"])
else:
    imagen_cargada = st.camera_input("Toma una foto al residuo con tu dispositivo")

if imagen_cargada is not None:
    st.image(imagen_cargada, caption="Imagen a procesar", use_column_width=True)
    
    with st.spinner("Analizando objeto con YOLOv8..."):
        # Guardar temporalmente la imagen cargada
        with open("temp_image.jpg", "wb") as f:
            f.write(imagen_cargada.getbuffer())

        # Ejecutar la predicción de YOLO
        results = model("temp_image.jpg")
        
        detectado = False
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                obj_name = model.names[cls_id]
                conf = float(box.conf[0])
                
                st.info(f"🔍 Objeto detectado: **{obj_name}** (Confianza: {conf:.2f})")
                detectado = True

                # Lógica de clasificación, mensajes complementarios y envío por MQTT al Wokwi
                if obj_name in ['bottle', 'cup', 'can', 'wine glass']:
                    st.success("⬜ **Material Reciclable** -> Contenedor Blanco (Plásticos/Latas)")
                    st.markdown("💡 **Consejo de manejo:** Asegúrate de que los objetos no estén contaminados con comida o líquidos; dales un enjuague rápido con agua y aplástalos si es posible para optimizar espacio.")
                    publish.single("ecosort/actidad", "BLAN", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: Reciclable!")
                    
                elif obj_name in ['apple', 'banana', 'orange', 'sandwich', 'carrot', 'potted plant', 'brocolli']:
                    st.info("🟩 **Residuo Orgánico** -> Contenedor Verde (Restos orgánicos)")
                    st.markdown("💡 **Consejo de manejo:** Estos restos son ideales para procesos de compostaje. Evita mezclarlos con plásticos, metales o aceites cocinados para mantener la calidad del abono.")
                    publish.single("ecosort/actidad", "VERDE", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: Orgánico!")
                    
                else:
                    st.warning("🟦 **Residuo Ordinario** -> Contenedor Negro (No reciclable)")
                    st.markdown("💡 **Consejo de manejo:** Este material no es aprovechable en cadenas de reciclaje tradicionales. Intenta reducir su consumo o buscar alternativas reutilizables a futuro.")
                    publish.single("ecosort/actidad", "AZUL", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: Ordinario!")
                break
            if detectado:
                break
        
        if not detectado:
            st.warning("No se reconoció un objeto claro. Intenta con mejor iluminación o acércate más.")
if "confirmacion_wokwi" not in st.session_state:
    st.session_state.confirmacion_wokwi = None

def consultar_confirmacion_mqtt(broker="broker.hivemq.com", topic="ecosort/confirmacion", timeout=1.5):
    resultado = {"payload": None}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe(topic)

    def on_message(client, userdata, msg):
        resultado["payload"] = msg.payload.decode("utf-8", errors="ignore").strip()

    # Compatible con paho-mqtt v2; si usas v1.x, quita CallbackAPIVersion.VERSION2
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, 1883, keepalive=10)
    client.loop_start()
    time.sleep(timeout)
    client.loop_stop()
    client.disconnect()
    return resultado["payload"]

st.divider()
st.subheader("🔘 Confirmación desde Wokwi")

if st.button("🔄 Comprobar confirmación del botón"):
    with st.spinner("Consultando tópico ecosort/confirmacion..."):
        msg_recibido = consultar_confirmacion_mqtt()
        if msg_recibido:
            st.session_state.confirmacion_wokwi = msg_recibido

if st.session_state.confirmacion_wokwi == "CONFIRMADO":
    st.success("✅ ¡Confirmación recibida desde Wokwi! El usuario validó la acción en el dispositivo.")
    if st.button("Limpiar confirmación"):
        st.session_state.confirmacion_wokwi = None
        st.rerun()
else:
    st.info("⏳ Esperando confirmación del botón en Wokwi (haz clic en *Comprobar confirmación del botón* y mientras carga pulsa el botón).")

st.write("@Jeremy Villa Patiño")
