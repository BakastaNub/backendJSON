from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos MySQL
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql://root:admin123@localhost/jsonreader')

print("Intentando conectar a la base de datos MySQL...")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para los archivos JSON
class JsonDocument(db.Model):
    __tablename__ = 'json_documents'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_cliente = db.Column(db.String(100))
    centro_comercial = db.Column(db.String(100))
    fecha_pago = db.Column(db.String(10))
    hora_pago = db.Column(db.String(10))
    modelo_placa = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    json_data = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

# Crear las tablas si no existen
with app.app_context():
    db.create_all()
    print("Tablas creadas/verificadas en la base de datos MySQL")

def to_camel_case(text):
    return ' '.join(word.capitalize() for word in text.split())

@app.route('/process-json', methods=['POST'])
def process_json():
    try:
        # Obtener datos del formulario
        issuer_name = request.form.get('issuerName')
        shopping_center = request.form.get('shoppingCenter')
        case_description = request.form.get('description')
        
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
            nombre_cliente = to_camel_case(nombre_cliente)
            
            # Procesar fecha y hora
            fecha_hora = datetime.strptime(json_data.get('InvoiceDate', ''), '%Y-%m-%d %H:%M:%S')
            fecha_formateada = fecha_hora.strftime('%d-%m-%y')
            hora_formateada = fecha_hora.strftime('%I:%M %p')
            
            # Obtener el modelo de placa
            items = json_data.get('items', [])
            modelo_placa = items[0].get('description', 'No especificado') if items else 'No especificado'
            
            # Actualizar el nombre del cliente si se proporciona
            if issuer_name:
                nombre_cliente = to_camel_case(issuer_name)
            
            processed_data = {
                'nombreCliente': nombre_cliente,
                'centroComercial': shopping_center,
                'fechaPago': fecha_formateada,
                'horaPago': hora_formateada,
                'modeloPlaca': modelo_placa,
                'descripcion': case_description
            }

            # Guardar en la base de datos si se proporciona una descripción
            if case_description:
                doc = JsonDocument(
                    nombre_cliente=nombre_cliente,
                    centro_comercial=shopping_center,
                    fecha_pago=fecha_formateada,
                    hora_pago=hora_formateada,
                    modelo_placa=modelo_placa,
                    descripcion=case_description,
                    json_data=json.dumps(json_data)
                )
                db.session.add(doc)
                db.session.commit()
                processed_data['id'] = doc.id
            
            return jsonify(processed_data)
            
        except json.JSONDecodeError:
            return jsonify({'error': 'El archivo no es un JSON válido'}), 400
        except ValueError as e:
            return jsonify({'error': f'Error al procesar la fecha: {str(e)}'}), 400
            
    except Exception as e:
        print(f"Error procesando el JSON: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/json-files', methods=['GET'])
def list_json_files():
    try:
        documents = JsonDocument.query.order_by(JsonDocument.fecha_creacion.desc()).all()
        files = []
        for doc in documents:
            files.append({
                'id': doc.id,
                'name': f"{doc.nombre_cliente} - {doc.fecha_pago}",
                'nombreCliente': doc.nombre_cliente,
                'centroComercial': doc.centro_comercial,
                'fechaPago': doc.fecha_pago,
                'horaPago': doc.hora_pago,
                'modeloPlaca': doc.modelo_placa,
                'descripcion': doc.descripcion
            })
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/json-file/<int:file_id>', methods=['GET'])
def get_json_file(file_id):
    try:
        print(f"Buscando archivo JSON con ID: {file_id}")
        document = JsonDocument.query.get(file_id)
        if not document:
            print(f"Archivo JSON con ID {file_id} no encontrado")
            return jsonify({'error': 'Archivo JSON no encontrado'}), 404
        
        print(f"Archivo JSON con ID {file_id} encontrado")
        return jsonify({
            'id': document.id,
            'nombreCliente': document.nombre_cliente,
            'centroComercial': document.centro_comercial,
            'fechaPago': document.fecha_pago,
            'horaPago': document.hora_pago,
            'modeloPlaca': document.modelo_placa,
            'descripcion': document.descripcion,
            'jsonData': json.loads(document.json_data)  # Asegurarse de devolver el JSON correctamente
        })
    except Exception as e:
        print(f"Error al obtener el archivo JSON: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        # Intenta hacer una consulta simple
        result = db.session.execute(db.text('SELECT 1')).scalar()
        return jsonify({
            'status': 'éxito',
            'mensaje': 'Conexión exitosa a la base de datos',
            'resultado': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'mensaje': f'Error de conexión: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
