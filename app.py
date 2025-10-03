import streamlit as st
import whisper
import tempfile
import os
from moviepy import (VideoFileClip)
import yt_dlp

# Set the title and a descriptive subtitle for the Streamlit app
st.set_page_config(page_title="Video to Transcript", layout="wide")
st.title("🎬 Universal Video Transcriber")
st.markdown("Upload a video file or paste a video URL (from TikTok, YouTube, etc.) to generate its audio transcript.")

# Cached function to load the Whisper model
# This prevents reloading the model every time the app reruns.
@st.cache_resource
def load_model():
    """Loads the Whisper speech-to-text model."""
    model = whisper.load_model("base")
    return model

# Load the model and display a message.
with st.spinner("Loading the speech-to-text model, this may take a moment..."):
    model = load_model()
st.success("Speech-to-text model loaded successfully.")


def transcribe_video(video_path, model):
    """
    Extracts audio from a video file, transcribes it, and returns the transcript.
    Cleans up the temporary audio file after processing.
    """
    transcript_text = None
    try:
        # Use moviepy to extract audio from the video file
        st.info("Extracting audio from the video...")
        video_clip = VideoFileClip(video_path)
        
        # Define a temporary path for the audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio_file:
            tmp_audio_path = tmp_audio_file.name

        # Write the audio to the temporary file
        video_clip.audio.write_audiofile(tmp_audio_path, codec='pcm_s16le')
        video_clip.close()

        # Transcribe the audio file using the Whisper model
        st.info("Audio extracted. Now transcribing...")
        result = model.transcribe(tmp_audio_path, fp16=False) # Set fp16=False if you don't have a GPU
        transcript_text = result["text"]

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
    finally:
        # Clean up the temporary audio file
        if 'tmp_audio_path' in locals() and os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)
    
    return transcript_text


# --- UI to choose input method ---
input_method = st.radio(
    "Choose your input method:",
    ("Upload a video file", "Paste a video URL (e.g., TikTok, YouTube)"),
    horizontal=True
)

transcript_text = None
transcript_filename = "transcript.txt"

# --- Handle the chosen input method ---
if input_method == "Upload a video file":
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=["mp4", "mov", "avi", "mkv", "webm"]
    )

    if uploaded_file is not None:
        video_filename = uploaded_file.name
        transcript_filename = f"{os.path.splitext(video_filename)[0]}_transcript.txt"

        with st.spinner("Processing uploaded video... This might take a while."):
            # Create a temporary file to store the uploaded video
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_filename)[1]) as tmp_video_file:
                tmp_video_file.write(uploaded_file.getvalue())
                tmp_video_path = tmp_video_file.name
            
            transcript_text = transcribe_video(tmp_video_path, model)
            os.remove(tmp_video_path) # Clean up the temporary video file

elif input_method == "Paste a video URL (e.g., TikTok, YouTube)":
    video_url = st.text_input("Enter the video URL:", placeholder="https://www.tiktok.com/@user/video/...")
    
    if st.button("Transcribe from URL") and video_url:
        with st.spinner("Downloading video from URL... Please wait."):
            try:
                # Create a temporary directory for the download
                with tempfile.TemporaryDirectory() as tmp_dir:
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': os.path.join(tmp_dir, 'downloaded_video.%(ext)s'),
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(video_url, download=True)
                        downloaded_file_path = ydl.prepare_filename(info_dict)

                    st.info("Download complete.")
                    transcript_text = transcribe_video(downloaded_file_path, model)

                    # Set a clean filename for the transcript download
                    base_filename = info_dict.get('title', 'video_transcript')
                    safe_filename = "".join([c for c in base_filename if c.isalpha() or c.isdigit() or c in (' ', '-')]).rstrip()
                    transcript_filename = f"{safe_filename}.txt"

            except Exception as e:
                st.error(f"Failed to download or process video. Please check the URL. Error: {e}")

# --- Display results if transcription was successful ---
if transcript_text:
    st.success("Transcription complete!")
    st.subheader("Generated Transcript:")
    st.text_area("Transcript", transcript_text, height=300)

    # Add a download button for the transcript text file
    st.download_button(
        label="Download Transcript",
        data=transcript_text.encode('utf-8'),
        file_name=transcript_filename,
        mime='text/plain'
    )

