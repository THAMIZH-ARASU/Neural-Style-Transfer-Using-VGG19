# app/frontend/app.py
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
API_URL = os.environ.get('API_URL', 'http://localhost:8000')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Check if both files are present
        if 'content_image' not in request.files or 'style_image' not in request.files:
            flash('Please upload both content and style images', 'error')
            return redirect(request.url)
        
        content_file = request.files['content_image']
        style_file = request.files['style_image']
        
        # Check if filenames are empty
        if content_file.filename == '' or style_file.filename == '':
            flash('Please select both files', 'error')
            return redirect(request.url)
        
        # Check if files are valid
        if not (content_file and allowed_file(content_file.filename) and 
                style_file and allowed_file(style_file.filename)):
            flash('Invalid file format. Please use PNG or JPG images.', 'error')
            return redirect(request.url)
        
        # Save files to upload API
        files = {
            'content_image': (content_file.filename, content_file.stream, content_file.content_type),
            'style_image': (style_file.filename, style_file.stream, style_file.content_type)
        }
        
        # Send to API
        response = requests.post(f"{API_URL}/upload/", files=files)
        
        if response.status_code == 200:
            data = response.json()
            # Store IDs in session
            return jsonify({
                'success': True,
                'content_id': data['content_id'],
                'style_id': data['style_id'],
                'message': 'Images uploaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API Error: {response.text}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/transfer', methods=['POST'])
def transfer_style():
    try:
        # Get form parameters
        data = {
            'content_id': request.form.get('content_id'),
            'style_id': request.form.get('style_id'),
            'content_weight': float(request.form.get('content_weight', 1.0)),
            'style_weight': float(request.form.get('style_weight', 1e6)),
            'steps': int(request.form.get('steps', 300)),
            'learning_rate': float(request.form.get('learning_rate', 0.003)),
            'conv1_1_weight': float(request.form.get('conv1_1_weight', 1.0)),
            'conv2_1_weight': float(request.form.get('conv2_1_weight', 0.8)),
            'conv3_1_weight': float(request.form.get('conv3_1_weight', 0.5)),
            'conv4_1_weight': float(request.form.get('conv4_1_weight', 0.3)),
            'conv5_1_weight': float(request.form.get('conv5_1_weight', 0.1))
        }
        
        # Send to API
        response = requests.post(f"{API_URL}/transfer/", data=data)
        
        if response.status_code == 200:
            result_data = response.json()
            
            # Download the result image and save locally
            result_id = result_data['result_id']
            img_data = result_data['preview'].split(',')[1]
            
            # Return the result
            return jsonify({
                'success': True, 
                'result_id': result_id,
                'preview': result_data['preview'],
                'progress': result_data['progress']
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API Error: {response.text}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/download/<result_id>')
def download_result(result_id):
    try:
        # Get download URL from API
        response = requests.get(f"{API_URL}/download/{result_id}")
        
        if response.status_code == 200:
            # Get image from API
            img_response = requests.get(f"{API_URL}{response.json()['download_url']}")
            
            if img_response.status_code == 200:
                # Save locally
                result_path = os.path.join(RESULTS_FOLDER, f"{result_id}.jpg")
                with open(result_path, 'wb') as f:
                    f.write(img_response.content)
                
                return send_from_directory(
                    os.path.dirname(result_path),
                    os.path.basename(result_path),
                    as_attachment=True,
                    download_name=f"neural_style_transfer_{result_id}.jpg"
                )
            else:
                flash('Error downloading the image', 'error')
                return redirect(url_for('index'))
        else:
            flash('Result not found', 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    try:
        # Check API health
        response = requests.get(f"{API_URL}/health")
        api_status = "Online" if response.status_code == 200 else "Offline"
        api_device = response.json().get('device', 'Unknown') if response.status_code == 200 else "Unknown"
        
        return jsonify({
            'status': 'healthy',
            'api_status': api_status,
            'api_device': api_device
        })
    except:
        return jsonify({
            'status': 'healthy',
            'api_status': 'Offline',
            'api_device': 'Unknown'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)