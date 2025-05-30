from flask import Flask, request, render_template, jsonify
import os
import subprocess
import requests
import shutil
from uuid import uuid4

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

# HTML template with status display
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
        .error { color: red; }
        .success { color: green; }
        #status { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Face Swapper</h1>
    <form method="post" action="{{ url_for('process') }}">
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
    <div id="status">{{ status|safe }}</div>
</body>
</html>
"""

# Write the HTML template to templates/index.html
os.makedirs(os.path.join(TEMPLATES_DIR, 'templates'), exist_ok=True)
with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w') as f:
    f.write(HTML_TEMPLATE)

@app.route('/')
def index():
    return render_template('index.html', status='')

@app.route('/process', methods=['POST'])
def process():
    source_image_url = request.form['source_image']
    target_video_url = request.form['target_video']
    
    # Initialize status
    status = ''
    
    try:
        # Download source image to /kaggle/working
        source_image_filename = f'source_{uuid4()}.jpg'
        source_image_path = os.path.join(OUTPUT_DIR, source_image_filename)
        response = requests.get(source_image_url, stream=True)
        if response.status_code == 200:
            with open(source_image_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        else:
            status = '<span class="error">Error: Failed to download source image</span>'
            if os.path.exists(source_image_path):
                os.remove(source_image_path)
            return render_template('index.html', status=status)
        
        # Download target video to /kaggle/working
        target_video_filename = f'target_{uuid4()}.mp4'
        target_video_path = os.path.join(OUTPUT_DIR, target_video_filename)
        response = requests.get(target_video_url, stream=True)
        if response.status_code == 200:
            with open(target_video_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        else:
            status = '<span class="error">Error: Failed to download target video</span>'
            if os.path.exists(source_image_path):
                os.remove(source_image_path)
            if os.path.exists(target_video_path):
                os.remove(target_video_path)
            return render_template('index.html', status=status)
        
        # Define output path in /kaggle/working
        # output_filename = f'output_{uuid4()}.mp4'
        # output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Execute the run.py script synchronously
        python_bin = '/usr/local/envs/py310/bin/python'
        run_script = 'run.py'
        cmd = [
            python_bin, run_script,
            '--execution-provider', 'cuda',
            '--execution-threads', '4',
            '-s', source_image_path,
            '-t', target_video_path,
            '-o', OUTPUT_DIR,
            '--frame-processor', 'face_swapper'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            status = f'<span class="success">Completed: Output saved to {output_path}</span>'
        except subprocess.CalledProcessError as e:
            status = f'<span class="error">Error during processing: {e.stderr}</span>'
        
        # Clean up temporary files (source and target)
        # if os.path.exists(source_image_path):
        #     os.remove(source_image_path)
        # if os.path.exists(target_video_path):
        #     os.remove(target_video_path)
        
    except Exception as e:
        status = f'<span class="error">Unexpected error: {str(e)}</span>'
        # Clean up in case of error
        # if os.path.exists(source_image_path):
        #     os.remove(source_image_path)
        # if os.path.exists(target_video_path):
        #     os.remove(target_video_path)
    
    return render_template('index.html', status=status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7860)
