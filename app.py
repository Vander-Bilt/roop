import gradio as gr
import os
import shutil
from uuid import uuid4
import subprocess
import os



# Assume you have a processing function that receives image and video paths
def process_media(image_path, video_path):

    print(f"Received image: {image_path}")
    print(f"Received video: {video_path}")

    # Check if image_path and video_path are None (e.g., if nothing was uploaded)
    if image_path is None:
        # You might want to raise an error or return a specific message to the user
        gr.Warning("Please upload an image.")
        return None
    if video_path is None:
        gr.Warning("Please upload a video.")
        return None

    # --- Create the target directory if it doesn't exist ---
    OUTPUT_DIR = "/kaggle/working/outputs"
    input_dir = "/kaggle/working/inputs"
    os.makedirs(input_dir, exist_ok=True) # exist_ok=True prevents an error if the directory already exists
    os.makedirs(OUTPUT_DIR, exist_ok=True) # exist_ok=True prevents an error if the directory already exists

    # --- Save the uploaded files to the desired directory ---
    # Get just the filename from the full path provided by Gradio
    image_filename = os.path.basename(image_path)
    video_filename = os.path.basename(video_path)

    # Construct the new paths in your desired directory
    src_image_path = os.path.join(input_dir, image_filename)
    src_video_path = os.path.join(input_dir, video_filename)

    # Copy the files from Gradio's temporary location to your target directory
    shutil.copy(image_path, src_image_path)
    shutil.copy(video_path, src_video_path)

    print(f"Image saved to: {src_image_path}")
    print(f"Video saved to: {src_video_path}") # This should be target_video_path for the video print statement

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
        '-s', src_image_path,
        '-t', src_video_path,
        '-o', output_path,
        '--frame-processor', 'face_swapper'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f'Completed: Output saved to {output_path}')
    except subprocess.CalledProcessError as e:
        print(f'Error during processing: {e.stderr}Stdout: {e.stdout}')


    return output_path


# Create Gradio interface
# inputs parameter is a list, corresponding to the order of your function parameters
# outputs parameter is also a list
demo = gr.Interface(
    fn=process_media,
    inputs=[
        gr.Image(label="上传图片", type="filepath"),  # Keep type="filepath" for image
        gr.Video(label="上传视频")                    # Remove type="filepath" here
    ],
    outputs=gr.Video(label="处理后的视频"),
    title="图片与视频合成应用",
    description="上传一张图片和一个视频，查看处理后的视频结果。"
)



# Launch Gradio application
print("启动 Gradio 应用...")
demo.launch(share=True, server_port=7860)
print("Gradio 应用已启动，请等待公共链接显示。")
