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

# Cargar Excel y normalizar
DATA_FILE = "data/Rutas_Completas_Principios_Contexto_Formato.xlsx"

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

df = pd.read_excel(DATA_FILE)
df.columns = [normalizar_texto(c) for c in df.columns]

# Variables para columnas
COL_PRINCIPIO = "principio iso"
COL_ENTORNO = "entorno general"
COL_INTERES = "interes vivencial"
COL_MODALIDAD = "modalidad sensorial preferida"
COL_TIPO = "ejemplo de formato"
COL_LINK = "link"

# Archivo CSV para respuestas
RESPUESTAS_FILE = "data/respuestas_usuarios.csv"
if not os.path.exists(RESPUESTAS_FILE):
    with open(RESPUESTAS_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fecha_hora", "nombre", "identificacion", "edad",
            "principio", "entorno", "interes", "modalidad", "fase", "respuesta",
            "pregunta1", "pregunta2", "pregunta3", "pregunta4", "pregunta5"
        ])

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
                data.get("pregunta1", ""),
                data.get("pregunta2", ""),
                data.get("pregunta3", ""),
                data.get("pregunta4", ""),
                data.get("pregunta5", "")
            ])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generar_analogia", methods=["POST"])
def generar_analogia():
    print("📌 [LOG] Petición recibida en /api/generar_analogia")
    data = request.get_json()
    print("📌 [LOG] Datos recibidos:", data)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key or len(openai_api_key.strip()) == 0:
        return jsonify({"error": "No está configurada la API Key de OpenAI"}), 500

    try:
        client = OpenAI(api_key=openai_api_key)
    except Exception as e:
        return jsonify({"error": "No se pudo inicializar cliente OpenAI"}), 500

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
                "Analogías",
                analogia, "", "", "", "", ""
            ])

        return jsonify({"analogias": analogia})

    except Exception as e:
        return jsonify({"error": f"Fallo al generar analogía: {str(e)}"}), 500

@app.route("/api/ver_respuestas", methods=["GET"])
def ver_respuestas():
    try:
        if not os.path.exists(RESPUESTAS_FILE):
            return jsonify({"respuestas": []})

        df_respuestas = pd.read_csv(RESPUESTAS_FILE, encoding="utf-8").fillna("")

        # Calcular métricas para fase 6
        def calcular_fase6(row):
            RC = lambda_RA = lambda_CSD = Gi = Ci = None

            if row["fase"] == "Fase 6":
                # RC
                if row["pregunta1"] == "Sí":
                    RC = 0.9
                elif row["pregunta1"] == "Regular":
                    RC = 0.6
                elif row["pregunta1"] == "No":
                    RC = 0.3

                # λ_RA
                if row["pregunta2"] == "Generé mi propia analogía y la comparé":
                    lambda_RA = 0.3
                elif row["pregunta2"] == "Comprendí y usé la analogía dada":
                    lambda_RA = 0.2
                elif row["pregunta2"] == "Leí la analogía, pero no la entendí bien":
                    lambda_RA = 0.1
                elif row["pregunta2"] == "No usé ninguna analogía":
                    lambda_RA = 0.0

                # λ_CSD
                acciones = str(row["pregunta3"]).split(";")
                lambda_CSD = min(sum(0.1 for acc in acciones if acc.strip()), 0.3)

                # Gi
                if row["pregunta4"] == "Mucho":
                    Gi = 0.9
                elif row["pregunta4"] == "Algo":
                    Gi = 0.7
                elif row["pregunta4"] == "Poco":
                    Gi = 0.4
                elif row["pregunta4"] == "Nada":
                    Gi = 0.1

                # Ci
                if row["pregunta5"] == "Muy fácil":
                    Ci = 0.1
                elif row["pregunta5"] == "Manejable":
                    Ci = 0.3
                elif row["pregunta5"] == "Difícil":
                    Ci = 0.6
                elif row["pregunta5"] == "Muy difícil":
                    Ci = 0.9

                if None not in (RC, lambda_RA, lambda_CSD, Gi, Ci):
                    resultado = ((RC + lambda_RA + lambda_CSD) * Gi) / Ci
                    return RC, lambda_RA, lambda_CSD, Gi, Ci, resultado

            return RC, lambda_RA, lambda_CSD, Gi, Ci, None

        df_respuestas[["RC", "lambda_RA", "lambda_CSD", "Gi", "Ci", "resultado"]] = df_respuestas.apply(
            lambda row: pd.Series(calcular_fase6(row)), axis=1
        )

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)