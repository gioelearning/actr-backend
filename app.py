from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import unicodedata

app = Flask(__name__)
CORS(app)

# Ruta al archivo Excel
EXCEL_PATH = os.path.join("data", "Rutas_Completas_Principios_Contexto_Formato.xlsx")

# Función para limpiar tildes y normalizar texto
def normalizar(texto):
    """
    Convierte a minúsculas, elimina tildes y espacios extra para comparación robusta.
    """
    if not isinstance(texto, str):
        texto = str(texto)
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')  # Elimina tildes
    return texto

@app.route("/")
def inicio():
    return "✅ API ACTR-ANALOGIC en línea"

@app.route("/api/buscar_recurso", methods=["POST"])
def buscar_recurso():
    data = request.get_json()

    # Validar entrada
    campos_esperados = ['principio', 'entorno', 'interes', 'modalidad']
    if not all(k in data for k in campos_esperados):
        return jsonify({"error": "Faltan datos de entrada"}), 400

    try:
        # Leer el archivo Excel
        df = pd.read_excel(EXCEL_PATH)

        # Columnas clave del Excel
        columnas_clave = [
            'Principio ISO',
            'Entorno General',
            'Interés Vivencial',
            'Modalidad Sensorial Preferida'
        ]

        # Validar existencia de columnas en el archivo
        for col in columnas_clave + ['Ejemplo de Formato', 'Link']:
            if col not in df.columns:
                return jsonify({"error": f"Falta la columna '{col}' en el Excel"}), 500

        # Normalizar columnas clave
        for col in columnas_clave:
            df[col] = df[col].apply(normalizar)

        # Normalizar datos de entrada
        principio = normalizar(data['principio'])
        entorno = normalizar(data['entorno'])
        interes = normalizar(data['interes'])
        modalidad = normalizar(data['modalidad'])

        # Filtrar coincidencias
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

# Ejecutar localmente o en Render
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)