from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import unicodedata
import csv
import os
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)
# CORS para todo (incluye preflight OPTIONS)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ---------- Utilidades ----------
DATA_FILE = "data/Rutas_Completas_Principios_Contexto_Formato.xlsx"
RESPUESTAS_FILE = "data/respuestas_usuarios.csv"

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

def to_float(x, default=0.0):
    """Convierte seguro a float (recibe None/str/num)."""
    try:
        if x is None or x == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)

# Cargar Excel y normalizar columnas
df = pd.read_excel(DATA_FILE)
df.columns = [normalizar_texto(c) for c in df.columns]
COL_PRINCIPIO = "principio iso"
COL_ENTORNO   = "entorno general"
COL_INTERES   = "interes vivencial"
COL_MODALIDAD = "modalidad sensorial preferida"
COL_TIPO      = "ejemplo de formato"
COL_LINK      = "link"

# Asegurar CSV con cabeceras
if not os.path.exists(RESPUESTAS_FILE):
    os.makedirs(os.path.dirname(RESPUESTAS_FILE), exist_ok=True)
    with open(RESPUESTAS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fecha_hora", "nombre", "identificacion", "edad",
            "principio", "entorno", "interes", "modalidad",
            "fase", "respuesta",
            "RC", "lambdaRA", "lambdaCSD", "Gi", "Ci", "RCplus", "Ui", "Ppi"
        ])

# ---------- Rutas ----------
@app.route("/")
def home():
    return "✅ API ACTR-ANALOGIC en línea"

@app.route("/api/buscar_recurso", methods=["POST", "OPTIONS"])
def buscar_recurso():
    if request.method == "OPTIONS":
        return ("", 200)
    data = request.get_json(force=True) or {}
    principio = normalizar_texto(data.get("principio"))
    entorno   = normalizar_texto(data.get("entorno"))
    interes   = normalizar_texto(data.get("interes"))
    modalidad = normalizar_texto(data.get("modalidad"))

    filtro = df[
        (df[COL_PRINCIPIO].apply(normalizar_texto) == principio) &
        (df[COL_ENTORNO].apply(normalizar_texto)   == entorno) &
        (df[COL_INTERES].apply(normalizar_texto)   == interes) &
        (df[COL_MODALIDAD].apply(normalizar_texto) == modalidad)
    ]
    if filtro.empty:
        return jsonify({"error": "No se encontró recurso para esta combinación"}), 404

    fila = filtro.iloc[0]
    return jsonify({"tipo": fila[COL_TIPO], "link": fila[COL_LINK]})

@app.route("/api/registrar_respuesta", methods=["POST", "OPTIONS"])
def registrar_respuesta():
    """
    Para fases anteriores (Recurso inicial / Analogías). NO hace cálculos.
    """
    if request.method == "OPTIONS":
        return ("", 200)
    data = request.get_json(force=True) or {}

    try:
        with open(RESPUESTAS_FILE, "a", newline="", encoding="utf-8") as f:
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
                "", "", "", "", "", "", "", ""  # columnas de métricas vacías
            ])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generar_analogia", methods=["POST", "OPTIONS"])
def generar_analogia():
    if request.method == "OPTIONS":
        return ("", 200)

    data = request.get_json(force=True) or {}
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key or len(openai_api_key.strip()) == 0:
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

        # Registrar fila de Analogías (sin métricas)
        with open(RESPUESTAS_FILE, "a", newline="", encoding="utf-8") as f:
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
                "Analogías",
                analogia,
                "", "", "", "", "", "", "", ""
            ])

        return jsonify({"analogias": analogia})
    except Exception as e:
        return jsonify({"error": f"Fallo al generar analogía: {str(e)}"}), 500

@app.route("/api/guardar_evaluacion", methods=["POST", "OPTIONS"])
def guardar_evaluacion():
    """
    Recibe selecciones de Fase 6, hace CÁLCULOS en backend y guarda métricas.
    Espera:
      rc, ra, csd (suma o lista), gi, ci  (valores numéricos 0..1)
      + contexto del estudiante (nombre, identificacion, edad, principio, entorno, interes, modalidad)
    """
    if request.method == "OPTIONS":
        return ("", 200)
    data = request.get_json(force=True) or {}

    # Parseo robusto
    RC        = to_float(data.get("rc"))
    lambdaRA  = to_float(data.get("ra"))
    # csd puede venir como número o lista de 0.1; clamp a 0.3
    csd_val = data.get("csd", 0)
    if isinstance(csd_val, list):
        lambdaCSD = sum(to_float(v) for v in csd_val)
    else:
        lambdaCSD = to_float(csd_val)
    lambdaCSD = min(lambdaCSD, 0.3)

    Gi = to_float(data.get("gi"))
    Ci = to_float(data.get("ci"))

    # Cálculos
    RCplus = RC + lambdaRA + lambdaCSD
    Ui = Gi - Ci
    theta = 0.2
    try:
        Ppi = float(pd.np.exp(Ui/theta) / pd.np.exp(Ui/theta))  # 1 producción => 1
    except Exception:
        Ppi = 1.0

    # Escribir fila
    try:
        with open(RESPUESTAS_FILE, "a", newline="", encoding="utf-8") as f:
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
                "",  # columna "respuesta" se deja vacía en fase 6
                RC, lambdaRA, lambdaCSD, Gi, Ci, RCplus, Ui, Ppi
            ])
        return jsonify({
            "status": "ok",
            "metrics": {"RC":RC, "lambdaRA":lambdaRA, "lambdaCSD":lambdaCSD,
                        "Gi":Gi, "Ci":Ci, "RCplus":RCplus, "Ui":Ui, "Ppi":Ppi}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ver_respuestas", methods=["GET"])
def ver_respuestas():
    try:
        if not os.path.exists(RESPUESTAS_FILE):
            return jsonify({"respuestas": []})
        df_respuestas = pd.read_csv(RESPUESTAS_FILE, encoding="utf-8").fillna("")
        return jsonify({"respuestas": df_respuestas.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/descargar_respuestas", methods=["GET"])
def descargar_respuestas():
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

# Alias solicitado por el admin (misma respuesta que /api/descargar_respuestas)
@app.route("/api/descargar_excel", methods=["GET"])
def descargar_excel_alias():
    return descargar_respuestas()

# (Opcional) reset que ya probaste desde el admin
@app.route("/api/reset_respuestas", methods=["POST"])
def reset_respuestas():
    try:
        os.makedirs(os.path.dirname(RESPUESTAS_FILE), exist_ok=True)
        with open(RESPUESTAS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "fecha_hora", "nombre", "identificacion", "edad",
                "principio", "entorno", "interes", "modalidad",
                "fase", "respuesta",
                "RC", "lambdaRA", "lambdaCSD", "Gi", "Ci", "RCplus", "Ui", "Ppi"
            ])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)