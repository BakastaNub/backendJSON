from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

def to_camel_case(text):
    return ' '.join(word.capitalize() for word in text.split())

@app.route('/process-json', methods=['POST'])
def process_json():
    try:
        # Obtener datos del formulario
        issuer_name = request.form.get('issuerName')
        shopping_center = request.form.get('shoppingCenter')
        case_description = request.form.get('description')  # Descripción del caso que ingresa el usuario
        
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        try:
            # Leer el JSON
            json_data = json.load(file)
            
            # Determinar el nombre del cliente
            electronic_data = json_data.get('ElectronicData', {})
            is_consumidor_final = (
                electronic_data.get('name1') == 'Consumidor' and 
                electronic_data.get('lastname1') == 'Final'
            )
            
            nombre_cliente = issuer_name if is_consumidor_final else f"{electronic_data.get('name1', '')} {electronic_data.get('lastname1', '')}".strip()
            nombre_cliente = to_camel_case(nombre_cliente)  # Convertir a camel case
            
            # Procesar fecha y hora
            fecha_hora = datetime.strptime(json_data.get('InvoiceDate', ''), '%Y-%m-%d %H:%M:%S')
            fecha_formateada = fecha_hora.strftime('%d-%m-%y')
            hora_formateada = fecha_hora.strftime('%I:%M %p')
            
            # Obtener el modelo de placa del campo description del primer elemento en items
            items = json_data.get('items', [])
            modelo_placa = items[0].get('description', 'No especificado') if items else 'No especificado'
            
            # Actualizar el nombre del cliente si se proporciona un nombre en el campo del formulario
            if issuer_name:
                nombre_cliente = to_camel_case(issuer_name)
            
            processed_data = {
                'nombreCliente': nombre_cliente,
                'centroComercial': shopping_center,
                'fechaPago': fecha_formateada,
                'horaPago': hora_formateada,
                'modeloPlaca': modelo_placa,  # Este es el valor del campo description del primer elemento en items
                'descripcion': case_description  # Esta es la descripción que ingresa el usuario
            }
            
            return jsonify(processed_data)
            
        except json.JSONDecodeError:
            return jsonify({'error': 'El archivo no es un JSON válido'}), 400
        except ValueError as e:
            return jsonify({'error': f'Error al procesar la fecha: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
