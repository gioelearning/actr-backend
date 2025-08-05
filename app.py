from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os

# Crear la app Flask
app = Flask(__name__)
CORS(app)

# Ruta al archivo Excel
EXCEL_PATH = os.path.join("data", "Rutas_Completas_Principios_Contexto_Formato.xlsx")

@app.route("/")
def inicio():
    return "✅ API ACTR-ANALOGIC en línea"

@app.route("/api/buscar_recurso", methods=["POST"])
def buscar_recurso():
    data = request.get_json()

    # Validar que los datos esperados estén presentes
    required_keys = ['principio', 'entorno', 'interes', 'modalidad']
    if not all(key in data for key in required_keys):
        return jsonify({"error": "Faltan datos de entrada"}), 400

    try:
        # Leer el Excel
        df = pd.read_excel(EXCEL_PATH)

        # Normalizar columnas para evitar errores por espacios y mayúsculas
        for col in df.columns[:4]:
            df[col] = df[col].astype(str).str.strip().str.lower()

        # Convertir los datos recibidos
        principio = data['principio'].strip().lower()
        entorno = data['entorno'].strip().lower()
        interes = data['interes'].strip().lower()
        modalidad = data['modalidad'].strip().lower()

        # Filtrar coincidencias
        resultado = df[
            (df.iloc[:, 0] == principio) &
            (df.iloc[:, 1] == entorno) &
            (df.iloc[:, 2] == interes) &
            (df.iloc[:, 3] == modalidad)
        ]

        if resultado.empty:
            return jsonify({"error": "No se encontró recurso para esta combinación"}), 404

        recurso = {
            "tipo": resultado.iloc[0, 4],
            "link": resultado.iloc[0, 5]
        }

        return jsonify(recurso)

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


# Ejecutar localmente o en Render
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)