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

# ------------------------------
# Configuración de rutas de datos
# ------------------------------
DATA_FILE = "data/Rutas_Completas_Principios_Contexto_Formato.xlsx"
RESPUESTAS_FILE = "data/respuestas_usuarios.csv"

# ------------------------------
# Funciones auxiliares
# ------------------------------
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

# ------------------------------
# Cargar base de principios ISO
# ------------------------------
df = pd.read_excel(DATA_FILE)
df.columns = [normalizar_texto(c) for c in df.columns]

COL_PRINCIPIO = "principio iso"
COL_ENTORNO = "entorno general"
COL_INTERES = "interes vivencial"
COL_MODALIDAD = "modalidad sensorial preferida"
COL_TIPO = "ejemplo de formato"
COL_LINK = "link"

# ------------------------------
# Crear CSV si no existe
# ------------------------------
if not os.path.exists(RESPUESTAS_FILE):
    with open(RESPUESTAS_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fecha_hora", "nombre", "identificacion", "edad",
            "principio", "entorno", "interes", "modalidad",
            "fase", "respuesta",
            "RC", "lambdaRA", "lambdaCSD", "Gi", "Ci", "RCplus", "Ui", "Ppi"
        ])

# ------------------------------
# Rutas API
# ------------------------------
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
    """
    Guarda cualquier respuesta (fases 1 a 5)
    """
    data = request.get_json()
    try:
        with open(RESPUESTAS_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data.get("nombre", ""),
                data.get("identificacion", ""),
                data.get("edad", ""),
                data.get("principio", ""),
                data.get("entorno", ""),
                data.get("interes", ""),
                data.get("modalidad", ""),
                data.get("fase", ""),
                data.get("respuesta", ""),
                data.get("RC", ""),
                data.get("lambdaRA", ""),
                data.get("lambdaCSD", ""),
                data.get("Gi", ""),
                data.get("Ci", ""),
                data.get("RCplus", ""),
                data.get("Ui", ""),
                data.get("Ppi", "")
            ])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fase6", methods=["POST"])
def fase6():
    """
    Procesa la Evaluación Cognitiva del Aprendizaje
    Calcula y guarda los valores en el CSV
    """
    data = request.get_json()

    # Mapas de valores según el cliente
    mapa_RC = {"Si": 0.9, "Regular": 0.6, "No": 0.3}
    mapa_lambdaRA = {
        "Genere": 0.3,
        "Comprendi": 0.2,
        "Lei": 0.1,
        "No use": 0.0
    }
    mapa_Gi = {"Mucho": 0.9, "Algo": 0.7, "Poco": 0.4, "Nada": 0.1}
    mapa_Ci = {"Muy facil": 0.1, "Manejable": 0.3, "Dificil": 0.6, "Muy dificil": 0.9}
    mapa_CSD = {
        "Consulté con el chatbot": 0.1,
        "Leí comentarios de compañeros": 0.1,
        "Recibí retroalimentación del docente": 0.1,
        "Participé en discusión grupal": 0.1,
        "Comparé mi respuesta con otra": 0.1
    }

    # Cálculos
    RC = mapa_RC.get(data.get("preg1", ""), "")
    lambdaRA = mapa_lambdaRA.get(data.get("preg2", ""), "")
    lambdaCSD = sum(mapa_CSD.get(a, 0) for a in data.get("preg3", []))
    Gi = mapa_Gi.get(data.get("preg4", ""), "")
    Ci = mapa_Ci.get(data.get("preg5", ""), "")

    # Fórmulas finales
    RCplus = round(RC + lambdaRA + lambdaCSD, 3) if RC != "" else ""
    Ui = round(Gi - Ci, 3) if Gi != "" and Ci != "" else ""
    Ppi = round(RCplus * Ui, 3) if RCplus != "" and Ui != "" else ""

    # Guardar en CSV
    try:
        with open(RESPUESTAS_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data.get("nombre", ""),
                data.get("identificacion", ""),
                data.get("edad", ""),
                data.get("principio", ""),
                data.get("entorno", ""),
                data.get("interes", ""),
                data.get("modalidad", ""),
                "Evaluación Cognitiva",
                data.get("respuesta", ""),
                RC, lambdaRA, lambdaCSD, Gi, Ci, RCplus, Ui, Ppi
            ])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generar_analogia", methods=["POST"])
def generar_analogia():
    data = request.get_json()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return jsonify({"error": "No está configurada la API Key de OpenAI"}), 500

    try:
        client = OpenAI(api_key=openai_api_key)
        prompt = f"""
        Eres un asistente educativo. Genera una analogía clara y fácil de entender sobre el principio ISO "{data.get('principio')}".
        Contexto del estudiante: entorno = "{data.get('entorno')}", interés = "{data.get('interes')}", modalidad sensorial = "{data.get('modalidad')}".
        Usa un lenguaje amigable y relacionado con el interés del estudiante.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en generar analogías educativas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250
        )

        analogia = response.choices[0].message.content.strip()
        return jsonify({"analogias": analogia})

    except Exception as e:
        return jsonify({"error": f"Fallo al generar analogía: {str(e)}"}), 500

@app.route("/api/ver_respuestas", methods=["GET"])
def ver_respuestas():
    try:
        if not os.path.exists(RESPUESTAS_FILE):
            return jsonify({"respuestas": []})

        df_respuestas = pd.read_csv(RESPUESTAS_FILE, encoding="utf-8")
        df_respuestas = df_respuestas.fillna("")
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

# ------------------------------
# Ejecutar servidor
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)