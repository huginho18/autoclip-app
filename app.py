import streamlit as st
import yt_dlp
import whisper
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.config import change_settings
import os
import tempfile

# Configuración para que ImageMagick funcione en Linux/Cloud
# Nota: En Windows local puede requerir configurar la ruta manual
change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Auto-Clips Virales", layout="centered", page_icon="🎬")

st.title("🎬 Auto-Clips: De YouTube a TikTok")
st.markdown("Convierte videos horizontales en verticales con subtítulos automáticamente.")

# --- FUNCIONES ---

def download_video(url, output_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'overwrites': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@st.cache_resource
def load_whisper_model():
    # Usamos 'base' para equilibrio entre velocidad y precisión. 
    # Usa 'tiny' si el servidor es muy lento.
    return whisper.load_model("base")

def generate_subtitles(text, start, end, video_w):
    # Genera el clip de texto
    return TextClip(
        txt=text, 
        fontsize=40, 
        color='white', 
        font='Arial-Bold', 
        stroke_color='black', 
        stroke_width=2,
        method='caption',
        size=(video_w * 0.9, None)
    ).set_start(start).set_end(end).set_position(('center', 'center'))

# --- INTERFAZ ---

url = st.text_input("🔗 Pega el enlace de YouTube:")

# Opciones de configuración
col1, col2 = st.columns(2)
with col1:
    start_sec = st.number_input("Segundo de inicio:", min_value=0, value=0)
with col2:
    duration = st.number_input("Duración del clip (segundos):", min_value=15, max_value=60, value=30)

if st.button("⚡ Crear Clip Viral"):
    if not url:
        st.error("¡Necesitas poner un enlace!")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp()
        video_input_path = os.path.join(temp_dir, "input.mp4")
        video_output_path = os.path.join(temp_dir, "final_clip.mp4")

        try:
            # 1. Descarga
            status_text.text("⬇️ Descargando video...")
            download_video(url, video_input_path)
            progress_bar.progress(25)

            # 2. Procesamiento de Video
            status_text.text("✂️ Recortando y ajustando formato...")
            original_clip = VideoFileClip(video_input_path)
            
            # Validar duración
            if start_sec + duration > original_clip.duration:
                st.warning("El video es más corto que el tiempo seleccionado. Ajustando al final.")
                start_sec = max(0, original_clip.duration - duration)

            # Cortar el fragmento deseado
            subclip = original_clip.subclip(start_sec, start_sec + duration)

            # Transformar a Vertical (9:16)
            w, h = subclip.size
            target_ratio = 9/16
            new_width = h * target_ratio
            
            # Crop centrado (Center Crop)
            cropped_clip = subclip.crop(
                x1=(w/2 - new_width/2), 
                y1=0, 
                width=new_width, 
                height=h
            )
            final_clip = cropped_clip.resize(height=1280) # HD Vertical
            progress_bar.progress(50)

            # 3. Transcripción (IA)
            status_text.text("🧠 La IA está escuchando y escribiendo subtítulos...")
            # Guardamos temporalmente el audio para Whisper
            audio_path = os.path.join(temp_dir, "audio.mp3")
            final_clip.audio.write_audiofile(audio_path, logger=None)
            
            model = load_whisper_model()
            result = model.transcribe(audio_path)
            progress_bar.progress(75)

            # 4. Quemar Subtítulos
            status_text.text("🔥 Quemando subtítulos en el video...")
            subtitle_clips = []
            for segment in result['segments']:
                txt_clip = generate_subtitles(
                    segment['text'].upper().strip(), 
                    segment['start'], 
                    segment['end'], 
                    final_clip.w
                )
                subtitle_clips.append(txt_clip)

            video_with_subs = CompositeVideoClip([final_clip] + subtitle_clips)
            
            # Exportar
            video_with_subs.write_videofile(
                video_output_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=24,
                logger=None
            )
            progress_bar.progress(100)
            status_text.text("✅ ¡Completado!")

            # Mostrar resultado
            st.video(video_output_path)
            
            # Botón de descarga
            with open(video_output_path, "rb") as file:
                btn = st.download_button(
                    label="📥 Descargar Video",
                    data=file,
                    file_name="clip_viral.mp4",
                    mime="video/mp4"
                )

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
        
        finally:
            # Limpieza (opcional, el sistema operativo limpia tempfiles eventualmente)

            pass
