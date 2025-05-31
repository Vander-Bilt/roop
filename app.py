from flask import Flask, request, render_template
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
        input[type="text"], input[type="file"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .drop-area {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            margin-top: 10px;
        }
        .drop-area.highlight { border-color: purple; }
        input[type="submit"] { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 4px; }
        input[type="submit"]:hover { background-color: #45a049; }
        .error { color: red; }
        .success { color: green; }
        #status { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Face Swapper</h1>
    <form method="post" action="{{ url_for('process') }}" enctype="multipart/form-data">
        <div class="form-group">
            <label for="source_image_input">Source Image (URL or Drag/Drop File):</label>
            <input type="text" id="source_image_url" name="source_image_url" placeholder="Enter URL">
            <div class="drop-area" id="source_image_drop_area">
                Drag and drop a source image here, or click to select
                <input type="file" id="source_image_file" name="source_image_file" accept="image/*" style="display: none;">
            </div>
        </div>
        <div class="form-group">
            <label for="target_video_input">Target Video (URL or Drag/Drop File):</label>
            <input type="text" id="target_video_url" name="target_video_url" placeholder="Enter URL">
            <div class="drop-area" id="target_video_drop_area">
                Drag and drop a target video here, or click to select
                <input type="file" id="target_video_file" name="target_video_file" accept="video/*" style="display: none;">
            </div>
        </div>
        <input type="submit" id="submit-btn" value="Process">
    </form>
    <div id="status">{{ status|safe }}</div>

    <script>
        function setupFileDrop(urlInputId, fileInputId, dropAreaId) {
            const urlInput = document.getElementById(urlInputId);
            const fileInput = document.getElementById(fileInputId);
            const dropArea = document.getElementById(dropAreaId);

            dropArea.addEventListener('click', () => fileInput.click());

            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    urlInput.value = ''; // Clear URL if file is selected
                }
            });

            dropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropArea.classList.add('highlight');
            });

            dropArea.addEventListener('dragleave', () => {
                dropArea.classList.remove('highlight');
            });

            dropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                dropArea.classList.remove('highlight');
                if (e.dataTransfer.files.length > 0) {
                    fileInput.files = e.dataTransfer.files;
                    urlInput.value = ''; // Clear URL if file is dropped
                }
            });

            urlInput.addEventListener('input', () => {
                if (urlInput.value !== '') {
                    fileInput.value = null; // Clear file input if URL is typed
                }
            });
        }

        setupFileDrop('source_image_url', 'source_image_file', 'source_image_drop_area');
        setupFileDrop('target_video_url', 'target_video_file', 'target_video_drop_area');
    </script>
</body>
</html>
"""

# Write the HTML template to templates/index.html
os.makedirs(TEMPLATES_DIR, exist_ok=True)
with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w') as f:
    f.write(HTML_TEMPLATE)

def download_file(url, destination_path):
    """Helper function to download a file from a URL."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        with open(destination_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        return True, ""
    except requests.exceptions.RequestException as e:
        return False, f"Failed to download from URL: {e}"

@app.route('/')
def index():
    return render_template('index.html', status='')

@app.route('/process', methods=['POST'])
def process():
    source_image_url = request.form.get('source_image_url')
    target_video_url = request.form.get('target_video_url')
    source_image_file = request.files.get('source_image_file')
    target_video_file = request.files.get('target_video_file')
    
    status = ''
    source_image_path = None
    target_video_path = None

    try:
        # Handle source image input
        if source_image_file and source_image_file.filename:
            source_image_filename = f'source_{uuid4()}_{source_image_file.filename}'
            source_image_path = os.path.join(OUTPUT_DIR, source_image_filename)
            source_image_file.save(source_image_path)
        elif source_image_url:
            source_image_filename = f'source_{uuid4()}.jpg'
            source_image_path = os.path.join(OUTPUT_DIR, source_image_filename)
            success, error_msg = download_file(source_image_url, source_image_path)
            if not success:
                status = f'<span class="error">{error_msg}</span>'
                return render_template('index.html', status=status)
        else:
            status = '<span class="error">Please provide a source image URL or upload a file.</span>'
            return render_template('index.html', status=status)

        # Handle target video input
        if target_video_file and target_video_file.filename:
            target_video_filename = f'target_{uuid4()}_{target_video_file.filename}'
            target_video_path = os.path.join(OUTPUT_DIR, target_video_filename)
            target_video_file.save(target_video_path)
        elif target_video_url:
            target_video_filename = f'target_{uuid4()}.mp4'
            target_video_path = os.path.join(OUTPUT_DIR, target_video_filename)
            success, error_msg = download_file(target_video_url, target_video_path)
            if not success:
                status = f'<span class="error">{error_msg}</span>'
                # Clean up source image if it was downloaded/uploaded
                if source_image_path and os.path.exists(source_image_path):
                    os.remove(source_image_path)
                return render_template('index.html', status=status)
        else:
            status = '<span class="error">Please provide a target video URL or upload a file.</span>'
            # Clean up source image
            if source_image_path and os.path.exists(source_image_path):
                os.remove(source_image_path)
            return render_template('index.html', status=status)
        
        # Define output path in /kaggle/working
        output_filename = f'output_{uuid4()}.mp4'
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Execute the run.py script synchronously
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
            status = f'<span class="success">Completed: Output saved to {output_path}</span>'
        except subprocess.CalledProcessError as e:
            status = f'<span class="error">Error during processing: {e.stderr}<br>Stdout: {e.stdout}</span>'

        # Upload to Hugging Face dataset
        if os.path.exists(output_path):
            try:
                upload_cmd = ['huggingface-cli', 'upload', 'mmmgo/mydataset', output_path, os.path.basename(output_path), '--repo-type', 'dataset']
                upload_result = subprocess.run(upload_cmd, capture_output=True, text=True, check=True)
                status += f'<br><span class="success">Uploaded to Hugging Face: {upload_result.stdout}</span>'
            except subprocess.CalledProcessError as e:
                status += f'<br><span class="error">Error uploading to Hugging Face: {e.stderr}<br>Stdout: {e.stdout}</span>'
        else:
            status += '<br><span class="error">Output file not found for upload.</span>'

    except Exception as e:
        status = f'<span class="error">Unexpected error: {str(e)}</span>'
    finally:
        # Clean up temporary files (source and target)
        if source_image_path and os.path.exists(source_image_path):
            os.remove(source_image_path)
        if target_video_path and os.path.exists(target_video_path):
            os.remove(target_video_path)
            
    return render_template('index.html', status=status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7860)
