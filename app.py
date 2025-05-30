from flask import Flask, request, render_template, jsonify, flash, redirect, url_for
import os
import subprocess
import requests
import tempfile
import shutil
import threading
from uuid import uuid4
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for flash messages

# Create a templates directory for the HTML template
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

# Ensure /kaggle/working exists
OUTPUT_DIR = '/kaggle/working'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Store processing status
processing_status = {}

# HTML template with JavaScript for asynchronous status polling
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Face Swapper</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input[type="text"] { width: 100%; padding: 8px; }
        input[type="submit"] { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        input[type="submit"]:hover { background-color: #45a049; }
        input[type="submit"]:disabled { background-color: #cccccc; cursor: not-allowed; }
        .error { color: red; }
        .success { color: green; }
        #status { margin-top: 20px; }
    </style>
    <script>
        function checkStatus(taskId) {
            fetch('/status/' + taskId)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerText = data.status;
                    if (data.status !== 'Processing...') {
                        document.getElementById('submit-btn').disabled = false;
                    } else {
                        setTimeout(() => checkStatus(taskId), 1000);
                    }
                });
        }
        function startProcessing() {
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('status').innerText = 'Processing...';
        }
    </script>
</head>
<body>
    <h1>Face Swapper</h1>
    <form method="post" action="{{ url_for('process') }}" onsubmit="startProcessing()">
        <div class="form-group">
            <label for="source_image">Source Image URL:</label>
            <input type="text" id="source_image" name="source_image" required>
        </div>
        <div class="form-group">
            <label for="target_video">Target Video URL:</label>
            <input type="text" id="target_video" name="target_video" required>
        </div>
        <input type="submit" id="submit-btn" value="Process">
    </form>
    <div id="status"></div>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <p class="{{ category }}">{{ message }}</p>
            {% endfor %}
        {% endif %}
    {% endwith %}
</body>
</html>
"""

# Write the HTML template to templates/index.html
os.makedirs(os.path.join(TEMPLATES_DIR, 'templates'), exist_ok=True)
with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w') as f:
    f.write(HTML_TEMPLATE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    source_image_url = request.form['source_image']
    target_video_url = request.form['target_video']
    task_id = str(uuid4())
    
    # Create a temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    
    # Initialize status
    processing_status[task_id] = 'Processing...'
    
    def run_processing():
        try:
            # Download source image
            source_image_path = os.path.join(temp_dir, f'source_{uuid4()}.jpg')
            response = requests.get(source_image_url, stream=True)
            if response.status_code == 200:
                with open(source_image_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            else:
                processing_status[task_id] = f'Error: Failed to download source image'
                shutil.rmtree(temp_dir)
                return
            
            # Download target video
            target_video_path = os.path.join(temp_dir, f'target_{uuid4()}.mp4')
            response = requests.get(target_video_url, stream=True)
            if response.status_code == 200:
                with open(target_video_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            else:
                processing_status[task_id] = f'Error: Failed to download target video'
                shutil.rmtree(temp_dir)
                return
            
            # Define output path in /kaggle/working
            output_filename = f'output_{uuid4()}.mp4'
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            # Execute the run.py script
            python_bin = '/usr/local/envs/py310/bin/python'
            run_script = 'run.py'
            cmd = [
                python_bin, run_script,
                '--execution-provider', 'cuda',
                '--execution-threads', '4',
                '-s', source_image_path,
                '-t', target_video_path,
                '-o', output_path,
                '--frame-processor', 'face_swapper'
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                processing_status[task_id] = f'Completed: Output saved to {output_path}'
            except subprocess.CalledProcessError as e:
                processing_status[task_id] = f'Error during processing: {e.stderr}'
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
        
        except Exception as e:
            processing_status[task_id] = f'Unexpected error: {str(e)}'
            shutil.rmtree(temp_dir)

    # Start processing in a separate thread
    threading.Thread(target=run_processing, daemon=True).start()
    
    # Return task ID to the client for status polling
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    status = processing_status.get(task_id, 'Unknown task')
    return jsonify({'status': status})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7860)
