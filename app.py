#se supone que esta verisón funciona
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import unicodedata
import csv
import os
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# ------------------------
# Configuración de archivos
# ------------------------
DATA_FILE = "data/Rutas_Completas_Principios_Contexto_Formato.xlsx"
RESPUESTAS_FILE = "data/respuestas_usuarios.csv"

# ------------------------
# Normalizar texto
# ------------------------
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

# ------------------------
# Cargar Excel de rutas
# ------------------------
df = pd.read_excel(DATA_FILE)
df.columns = [normalizar_texto(c) for c in df.columns]

COL_PRINCIPIO = "principio iso"
COL_ENTORNO = "entorno general"
COL_INTERES = "interes vivencial"
COL_MODALIDAD = "modalidad sensorial preferida"
COL_TIPO = "ejemplo de formato"
COL_LINK = "link"

# ------------------------
# Columnas fijas del CSV
# ------------------------
COLUMNAS_RESPUESTAS = [
    "fecha_hora", "nombre", "identificacion", "edad",
    "principio", "entorno", "interes", "modalidad",
    "fase", "respuesta",
    "RC", "lambdaRA", "lambdaCSD", "Gi", "Ci", "RCplus", "Ui", "Ppi"
]

# Crear CSV vacío si no existe
os.makedirs("data", exist_ok=True)
if not os.path.exists(RESPUESTAS_FILE):
    with open(RESPUESTAS_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS_RESPUESTAS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

# ------------------------
# Rutas API
# ------------------------
@app.route("/")
def home():
    return "✅ API ACTR-ANALOGIC en línea"

@app.route("/api/buscar_recurso", methods=["POST"])
def buscar_recurso():
    data = request.get_json()
    principio = normalizar_texto(data.get("principio"))
    entorno = normalizar_texto(data.get("entorno"))
    interes = normalizar_texto(data.get("interes"))
    modalidad = normalizar_texto(data.get("modalidad"))

    filtro = df[
        (df[COL_PRINCIPIO].apply(normalizar_texto) == principio) &
        (df[COL_ENTORNO].apply(normalizar_texto) == entorno) &
        (df[COL_INTERES].apply(normalizar_texto) == interes) &
        (df[COL_MODALIDAD].apply(normalizar_texto) == modalidad)
    ]

    if filtro.empty:
        return jsonify({"error": "No se encontró recurso para esta combinación"}), 404

    fila = filtro.iloc[0]
    return jsonify({
        "tipo": fila[COL_TIPO],
        "link": fila[COL_LINK]
    })

@app.route("/api/registrar_respuesta", methods=["POST"])
def registrar_respuesta():
    data = request.get_json()

    print("📩 [DEBUG] Datos recibidos en /api/registrar_respuesta:")
    for k, v in data.items():
        print(f"   {k}: {v}")

    try:
        # Agregar fecha/hora actual si no viene
        data["fecha_hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Asegurar que todas las columnas existan
        for col in COLUMNAS_RESPUESTAS:
            if col not in data:
                data[col] = ""

        # Guardar en CSV
        with open(RESPUESTAS_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNAS_RESPUESTAS, quoting=csv.QUOTE_ALL)
            writer.writerow(data)

        print("✅ [DEBUG] Respuesta guardada correctamente en CSV.")
        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ [ERROR] No se pudo guardar la respuesta:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/generar_analogia", methods=["POST"])
def generar_analogia():
    data = request.get_json()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return jsonify({"error": "No está configurada la API Key de OpenAI"}), 500

    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
    Eres un asistente educativo. Genera una analogía clara y fácil de entender sobre el principio ISO "{data.get('principio')}".
    Contexto del estudiante: entorno = "{data.get('entorno')}", interés = "{data.get('interes')}", modalidad sensorial = "{data.get('modalidad')}".
    Usa un lenguaje amigable y relacionado con el interés del estudiante.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en generar analogías educativas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            timeout=15
        )

        analogia = response.choices[0].message.content.strip()

        # Guardar en CSV
        fila = {col: "" for col in COLUMNAS_RESPUESTAS}
        fila.update({
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nombre": data.get("nombre", ""),
            "identificacion": data.get("identificacion", ""),
            "edad": data.get("edad", ""),
            "principio": data.get("principio", ""),
            "entorno": data.get("entorno", ""),
            "interes": data.get("interes", ""),
            "modalidad": data.get("modalidad", ""),
            "fase": "Analogías",
            "respuesta": analogia
        })

        with open(RESPUESTAS_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNAS_RESPUESTAS, quoting=csv.QUOTE_ALL)
            writer.writerow(fila)

        return jsonify({"analogias": analogia})

    except Exception as e:
        return jsonify({"error": f"Fallo al generar analogía: {str(e)}"}), 500

@app.route("/api/ver_respuestas", methods=["GET"])
def ver_respuestas():
    try:
        if not os.path.exists(RESPUESTAS_FILE):
            return jsonify({"respuestas": []})

        df_respuestas = pd.read_csv(RESPUESTAS_FILE, encoding="utf-8").fillna("")
        return jsonify({"respuestas": df_respuestas.to_dict(orient="records")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/descargar_excel", methods=["GET"])
def descargar_excel():
    try:
        if not os.path.exists(RESPUESTAS_FILE):
            return "No hay datos", 404

        return app.response_class(
            open(RESPUESTAS_FILE, encoding="utf-8").read(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=respuestas_usuarios.csv"}
        )
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
