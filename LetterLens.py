from flask import Flask, render_template, request, redirect, url_for, flash
import cv2
import pytesseract
import os
from werkzeug.utils import secure_filename

# Configura la ubicación de Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Ajusta la ruta según sea necesario

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/imagenes'
# Necesario para que `flash` funcione en el index
app.secret_key = 'supersecretkey'

# Lista de extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Página principal con formulario de carga de imagen
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para procesar la imagen cargada
@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(request.url)
    
    file = request.files['image']
    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(request.url)
    
    # Verifica si el archivo es una imagen permitida
    if file and allowed_file(file.filename):
        # Guarda la imagen cargada
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Procesamiento de imagen con OpenCV y Tesseract
        image = cv2.imread(filepath)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Configuración de Tesseract para reconocimiento en español
        custom_config = r'--oem 3 --psm 6'
        recognized_text = pytesseract.image_to_string(thresh_image, lang='spa', config=custom_config)
        
        # Separar cada carácter del texto reconocido
        separated_characters = list(recognized_text.replace(" ", ""))  # Eliminar espacios si es necesario

        # Retorna los resultados a la página web
        return render_template('index.html', recognized_text=recognized_text, separated_characters=separated_characters, image_path=filepath)
    
    else:
        flash('Formato de archivo no permitido. Solo se aceptan archivos PNG, JPG y JPEG.')
        return redirect(request.url)
    

if __name__ == '__main__':
    app.run(debug=True)
