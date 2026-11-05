import streamlit as st
from ultralytics import YOLO
import paho.mqtt.publish as publish

# Configuración de la interfaz web
st.set_page_config(page_title="EcoSort - Asistente de Reconocimiento", page_icon="♻️", layout="centered")

st.title("♻️ EcoSort: Clasificador Inteligente de Residuos")
st.write("Sube una foto o usa tu cámara para identificar el residuo y enviar la orden inmediata al contenedor físico (Wokwi).")

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

                # Lógica de clasificación y envío por MQTT al Wokwi
                if obj_name in ['bottle', 'cup', 'can', 'wine glass']:
                    st.success("⬜ **Material Reciclable** -> Contenedor Blanco (Plásticos/Latas)")
                    publish.single("ecosort/actidad", "BLAN", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: BLAN!")
                elif obj_name in ['apple', 'banana', 'orange', 'sandwich', 'carrot']:
                    st.info("🟩 **Residuo Orgánico** -> Contenedor Verde (Restos orgánicos)")
                    publish.single("ecosort/actidad", "VERDE", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: VERDE")
                else:
                    st.warning("🟦 **Residuo Ordinario** -> Contenedor Negro (No reciclable)")
                    publish.single("ecosort/actidad", "AZUL", hostname="broker.hivemq.com")
                    st.toast("¡Señal enviada a Wokwi: AZUL!")
                break
            if detectado:
                break
        
        if not detectado:
            st.warning("No se reconoció un objeto claro. Intenta con mejor iluminación o acércate más.")
