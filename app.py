# app.py (completo - reemplaza/integra con tu versión actual)
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os
import unicodedata
from datetime import datetime
import csv

# OpenAI client (usa la librería oficial)
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# RUTAS DE DATOS
BASE_DATA_DIR = "data"
if not os.path.exists(BASE_DATA_DIR):
    os.makedirs(BASE_DATA_DIR)

EXCEL_PATH = os.path.join(BASE_DATA_DIR, "Rutas_Completas_Principios_Contexto_Formato.xlsx")
RESPUESTAS_CSV = os.path.join(BASE_DATA_DIR, "respuestas_estudiantes.csv")
ANALOGIAS_CSV = os.path.join(BASE_DATA_DIR, "analogias_generadas.csv")

# Normalización de texto (quita tildes, espacios y pasa a minúsculas)
def normalizar(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

@app.route("/")
def inicio():
    return "✅ API ACTR-ANALOGIC en línea"

# Endpoint existente para buscar recurso (se asume que ya tienes esta lógica)
@app.route("/api/buscar_recurso", methods=["POST"])
def buscar_recurso():
    data = request.get_json()
    required_keys = ['principio', 'entorno', 'interes', 'modalidad']
    if not all(k in data for k in required_keys):
        return jsonify({"error": "Faltan datos de entrada"}), 400
    try:
        df = pd.read_excel(EXCEL_PATH)
        # columnas claves según tu Excel
        columnas_clave = [
            'Principio ISO',
            'Entorno General',
            'Interés Vivencial',
            'Modalidad Sensorial Preferida'
        ]
        for col in columnas_clave + ['Ejemplo de Formato', 'Link']:
            if col not in df.columns:
                return jsonify({"error": f"Falta la columna '{col}' en el Excel"}), 500
        for col in columnas_clave:
            df[col] = df[col].apply(normalizar)

        principio = normalizar(data['principio'])
        entorno = normalizar(data['entorno'])
        interes = normalizar(data['interes'])
        modalidad = normalizar(data['modalidad'])

        resultado = df[
            (df['Principio ISO'] == principio) &
            (df['Entorno General'] == entorno) &
            (df['Interés Vivencial'] == interes) &
            (df['Modalidad Sensorial Preferida'] == modalidad)
        ]

        if resultado.empty:
            return jsonify({"error": "No se encontró recurso para esta combinación"}), 404

        recurso = {
            "tipo": resultado.iloc[0]['Ejemplo de Formato'],
            "link": resultado.iloc[0]['Link']
        }
        return jsonify(recurso)

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

# Endpoint para registrar respuesta (actualizado para guardar datos personales y recurso)
@app.route("/api/registrar_respuesta", methods=["POST"])
def registrar_respuesta():
    data = request.get_json()
    # Campos esperados (se requieren los personales y contexto)
    required_fields = [
        'nombre_completo', 'numero_identificacion', 'edad',
        'principio', 'entorno', 'interes', 'modalidad',
        'tipo_recurso', 'link_recurso', 'respuesta', 'fase'
    ]
    if not all(k in data for k in required_fields):
        return jsonify({"error": "Datos incompletos para registrar respuesta"}), 400
    try:
        nuevo_registro = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nombre_completo": data["nombre_completo"],
            "numero_identificacion": data["numero_identificacion"],
            "edad": data["edad"],
            "principio": data["principio"],
            "entorno": data["entorno"],
            "interes": data["interes"],
            "modalidad": data["modalidad"],
            "tipo_recurso": data["tipo_recurso"],
            "link_recurso": data["link_recurso"],
            "respuesta": data["respuesta"],
            "fase": data["fase"]
        }

        archivo_nuevo = not os.path.exists(RESPUESTAS_CSV)
        with open(RESPUESTAS_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=nuevo_registro.keys())
            if archivo_nuevo:
                writer.writeheader()
            writer.writerow(nuevo_registro)

        return jsonify({"mensaje": "Respuesta registrada exitosamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para generar analogía con OpenAI (usa la plantilla del notebook)
@app.route("/api/generar_analogia", methods=["POST"])
def generar_analogia():
    data = request.get_json()
    # Esperamos datos contextuales mínimos y el estilo opcional
    required = ['nombre_completo','numero_identificacion','principio','entorno','interes','modalidad','tipo_recurso','link_recurso']
    if not all(k in data for k in required):
        return jsonify({"error": "Datos incompletos para generar analogía"}), 400

    try:
        # Construir prompt usando plantilla (adaptada desde el notebook)
        principio = data['principio']
        interes = data['interes']
        entorno = data['entorno']
        modalidad = data['modalidad']

        # Si el cliente proporcionó un prompt base personalizado, podemos incluirlo
        estilo = data.get('estilo', 'general')
        # Plantilla: ajusta según lo que el cliente envíe
        prompt = f"""
Actúa como una experta en pedagogía y razonamiento analógico.
Utiliza un enfoque de analogías contextualizadas.

Dominio base (contexto conocido): {entorno}, con interés vivencial en {interes}.
Dominio objetivo: el principio ISO "{principio}".
Modalidad sensorial preferida: {modalidad}.

Genera una analogía educativa clara, breve (máx 120-180 palabras),
con correspondencias estructurales y un ejemplo práctico aplicable al contexto del estudiante.
"""

        # Obtener API key desde variables de entorno en Render
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "OpenAI API key no configurada en variables de entorno"}), 500

        client = OpenAI(api_key=api_key)

        # Llamada al endpoint de chat/completions (modelo configurable)
        # Atención: el modelo y método pueden cambiar según la versión de la librería OpenAI
        respuesta = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres una experta en pedagogía y razonamiento analógico."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )

        analogia_generada = respuesta.choices[0].message.content.strip()

        # Guardar la analogía para auditoría
        registro_analog = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nombre_completo": data.get("nombre_completo", ""),
            "numero_identificacion": data.get("numero_identificacion", ""),
            "principio": principio,
            "interes": interes,
            "entorno": entorno,
            "modalidad": modalidad,
            "prompt": prompt,
            "analogia": analogia_generada
        }
        archivo_nuevo = not os.path.exists(ANALOGIAS_CSV)
        with open(ANALOGIAS_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=registro_analog.keys())
            if archivo_nuevo:
                writer.writeheader()
            writer.writerow(registro_analog)

        return jsonify({"analogia": analogia_generada})

    except Exception as e:
        return jsonify({"error": f"Error al generar analogía: {str(e)}"}), 500

# Endpoint admin para descargar CSV de respuestas (PROTEGIDO por ADMIN_KEY)
@app.route("/admin/download_respuestas", methods=["GET"])
def admin_download_respuestas():
    key = request.args.get("key")
    admin_key = os.environ.get("ADMIN_KEY")
    if not admin_key or key != admin_key:
        return ("Unauthorized", 401)
    if not os.path.exists(RESPUESTAS_CSV):
        return ("No hay datos", 404)
    return send_file(RESPUESTAS_CSV, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)