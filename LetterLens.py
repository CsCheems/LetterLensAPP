import os
import cv2
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Ajusta la ruta según sea necesario

# Configuración del entorno
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/imagenes'  # Carpeta para imágenes subidas
app.config['TEMP_LETTER_FOLDER'] = 'static/temp_letters'  # Carpeta para letras recortadas temporalmente
app.secret_key = 'supersecretkey'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Asegúrate de crear el directorio para las letras temporales si no existe
if not os.path.exists(app.config['TEMP_LETTER_FOLDER']):
    os.makedirs(app.config['TEMP_LETTER_FOLDER'])

# Función para verificar las extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para la página principal con formulario de carga de imagen
@app.route('/')
def index():
    cleanup_temp_images()
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
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        image = cv2.imread(filepath)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)
        
        custom_config = r'--oem 3 --psm 6'
        recognized_text = pytesseract.image_to_string(thresh_image, lang='spa', config=custom_config)
        
        # Extraer cada letra y su posición
        boxes = pytesseract.image_to_boxes(thresh_image, lang='spa')
        letters = []
        
        for box in boxes.splitlines():
            b = box.split()
            char = b[0]
            x, y, w, h = int(b[1]), int(b[2]), int(b[3]), int(b[4])
            cropped_letter = image[image.shape[0] - h:image.shape[0] - y, x:w]
            
            # Guardar la letra recortada como archivo temporal
            temp_letter_path = os.path.join(app.config['TEMP_LETTER_FOLDER'], f"{char}_{x}_{y}.png")
            cv2.imwrite(temp_letter_path, cropped_letter)
            
            # Convertir la imagen a base64 para mostrar en la interfaz
            _, buffer = cv2.imencode('.png', cropped_letter)
            letter_base64 = base64.b64encode(buffer).decode('utf-8')
            letters.append({'char': char, 'img_data': letter_base64, 'path': temp_letter_path, 'coords': (x, y, w, h)})
        
        # Guardar los datos en la sesión
        session['recognized_text'] = recognized_text
        session['letters'] = [{'char': letter['char'], 'path': letter['path']} for letter in letters]
        session['image_path'] = filename
        print("Letras generadas:", letters)
        return render_template('index.html', recognized_text=recognized_text, letters=letters, image_path=filename)
    
    else:
        flash('Formato de archivo no permitido. Solo se aceptan archivos PNG, JPG y JPEG.')
        return redirect(request.url)

# Ruta para procesar las correcciones
@app.route('/process_corrections', methods=['POST'])
def process_corrections():
    print("Session letters:", session.get('letters'))
    action = request.form.get('action')
    if action.startswith('remove_'):
        indice_letra_a_eliminar = int(action.split('_')[1])
        letters = session.get('letters', [])
        letra_a_eliminar = letters.pop(indice_letra_a_eliminar)
        if os.path.exists(letra_a_eliminar['path']):
            os.remove(letra_a_eliminar['path'])
        
        session['letters'] = letters
        flash('Letra Eliminada')

    elif action == 'save':
        letters = session.get('letters', [])
        for idx in enumerate(letters):
            corrected_char = request.form.get(f'letters[{idx}]')
            if corrected_char:
                letters[idx]['char'] = corrected_char
        session['letters'] = letters
        flash('Correcciones guardadas')

    recognized_text = session.get('recognized_text')
    filename = session.get('image_path')
    
    return render_template('index.html', recognized_text=recognized_text, letters=letters, image_path=filename)


# Ruta para limpiar las imágenes temporales
@app.route('/cleanup_temp_images')
def cleanup_temp_images():
    # Eliminar todas las imágenes temporales
    for filename in os.listdir(app.config['TEMP_LETTER_FOLDER']):
        file_path = os.path.join(app.config['TEMP_LETTER_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    flash('Las imágenes temporales se han eliminado.')
    return redirect(url_for('index'))

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
