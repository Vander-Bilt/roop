from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import os
import subprocess
import requests
import tempfile
import shutil
from uuid import uuid4

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for flash messages

# Create a templates directory for the HTML template
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

# HTML template for the form
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
        <input type="submit" value="Process">
    </form>
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
    
    # Create a temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Download source image
        source_image_path = os.path.join(temp_dir, f'source_{uuid4()}.jpg')
        response = requests.get(source_image_url, stream=True)
        if response.status_code == 200:
            with open(source_image_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        else:
            flash('Failed to download source image', 'error')
            shutil.rmtree(temp_dir)
            return redirect(url_for('index'))
        
        # Download target video
        target_video_path = os.path.join(temp_dir, f'target_{uuid4()}.mp4')
        response = requests.get(target_video_url, stream=True)
        if response.status_code == 200:
            with open(target_video_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        else:
            flash('Failed to download target video', 'error')
            shutil.rmtree(temp_dir)
            return redirect(url_for('index'))
        
        # Define output path
        output_path = os.path.join(temp_dir, f'output_{uuid4()}.mp4')
        
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
            flash('Processing completed successfully!', 'success')
        except subprocess.CalledProcessError as e:
            flash(f'Error during processing: {e.stderr}', 'error')
            shutil.rmtree(temp_dir)
            return redirect(url_for('index'))
        
        # Serve the output file for download
        return send_file(
            output_path,
            as_attachment=True,
            download_name='output_video.mp4',
            mimetype='video/mp4'
        )
    
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        shutil.rmtree(temp_dir)
        return redirect(url_for('index'))
    
    finally:
        # Clean up temporary directory after sending the file
        # Use a separate thread or delay cleanup if needed, but for simplicity, we assume send_file completes
        pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
