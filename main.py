from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.requests import Request
from pydantic import BaseModel
from typing import List, Tuple, Optional, Union
import speech_recognition as sr
import google.generativeai as genai
from fastapi.staticfiles import StaticFiles
import tempfile
import os
import base64
import json
import subprocess
from pydub import AudioSegment
import uuid
from pathlib import Path
import asyncio
import shutil
from emotion_reg import recognize_text_and_emotion_from_audio, analyze_emotion_from_text

# Cấu hình Gemini
genai.configure(api_key='AIzaSyDuuYd4K81PgG9C00Onw-XgwgvJ93DYnqI')
model = genai.GenerativeModel(model_name='tunedModels/generate-emotion-response-1000')

os.environ["PYTHONIOENCODING"] = "utf-8"
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

TEMP_AUDIO_DIR = Path("temp_audio")
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# Đảm bảo thư mục assets/infore tồn tại
BASE_DIR = Path(__file__).resolve().parent  # Hoặc đường dẫn gốc dự án của bạn

# Thiết lập đường dẫn tuyệt đối đến thư mục assets
ASSETS_DIR = BASE_DIR / "tts" / "vietTTS" / "assets" / "infore"
ASSETS_DIR.mkdir(exist_ok=True, parents=True)

# Đường dẫn tuyệt đối đến file lexicon.txt
LEXICON_FILE = ASSETS_DIR / "lexicon.txt"

# Đường dẫn đến file lexicon.txt
LEXICON_FILE = ASSETS_DIR / "lexicon.txt"

class TTSRequest(BaseModel):
    text: str 

# Định nghĩa mô hình dữ liệu
class TextMessageData(BaseModel):
    message: str
    chat_history: List[Tuple[str, str]]

class AudioData(BaseModel):
    base64_audio: str
    chat_history: List[Tuple[str, str]]

class MessageRequest(BaseModel):
    message_type: str  # "text" hoặc "audio"
    content: Union[str, dict]  # Nội dung tin nhắn (text hoặc audio_data)
    chat_history: List[Union[Tuple[str, str], Tuple[str, str, str]]]

# Tạo đối tượng templates để render file HTML
templates = Jinja2Templates(directory="templates")

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Endpoint tạo file âm thanh từ văn bản tiếng Việt sử dụng VietTTS CLI
    """
    try:
        audio_id = str(uuid.uuid4())
        output_path = ASSETS_DIR / f"clip_{audio_id}.wav"
        
        # Đường dẫn tuyệt đối đến thư mục gốc của VietTTS
        vietTTS_root = Path("tts/vietTTS").absolute()
        
        # Chuẩn bị lệnh chạy VietTTS
        cmd = [
            "python", 
            "-m", 
            "vietTTS.synthesizer", 
            "--text", request.text,
            "--output", str(output_path),
            "--lexicon-file", str(LEXICON_FILE),
            "--silence-duration", "0.2"
        ]
        print(cmd)
        
        # Thiết lập môi trường với UTF-8
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Thực thi lệnh với thư mục làm việc được chỉ định
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            cwd=str(vietTTS_root),  # Chỉ định thư mục làm việc là thư mục gốc của VietTTS
            env=env,  # Sử dụng biến môi trường đã thiết lập
            text=True,  # Xử lý I/O dưới dạng text thay vì bytes
            encoding='utf-8'  # Đảm bảo xử lý đúng ký tự tiếng Việt
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Lỗi khi tạo âm thanh: {stderr.decode('utf-8')}")
            raise HTTPException(status_code=500, detail=f"VietTTS error: {stderr.decode('utf-8')}")
        
        # Copy file từ assets/infore vào thư mục tạm để phục vụ web
        temp_file_path = TEMP_AUDIO_DIR / f"{audio_id}.wav"
        shutil.copy2(output_path, temp_file_path)
        
        # Xóa file gốc trong assets/infore để tránh tích tụ file
        if output_path.exists():
            output_path.unlink()
        
        # Đăng ký file này để xóa sau khi phát
        return {"audio_url": f"/api/audio/{audio_id}.wav", "audio_id": audio_id}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """
    Endpoint để lấy file âm thanh đã tạo
    """
    file_path = TEMP_AUDIO_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh")
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.delete("/api/audio/{audio_id}")
async def delete_audio(audio_id: str):
    """
    Endpoint để xóa file âm thanh sau khi đã phát xong
    """
    file_path = TEMP_AUDIO_DIR / f"{audio_id}.wav"
    
    if file_path.exists():
        file_path.unlink()
        return {"success": True, "message": "File đã được xóa"}
    
    return {"success": False, "message": "File không tồn tại"}

# Định kỳ xóa các file âm thanh tạm
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_temp_files())

async def cleanup_temp_files():
    """
    Xóa các file âm thanh tạm cũ
    """
    import time
    while True:
        try:
            current_time = time.time()
            for file_path in TEMP_AUDIO_DIR.glob("*"):
                # Xóa file cũ hơn 1 giờ
                if current_time - file_path.stat().st_mtime > 3600:
                    file_path.unlink()
        except Exception as e:
            print(f"Lỗi khi dọn dẹp file tạm: {e}")
        
        # Kiểm tra mỗi 30 phút
        await asyncio.sleep(1800)

# API nhận dữ liệu tin nhắn (text hoặc audio) và trả về phản hồi
@app.post("/process_message")
async def process_message(data: MessageRequest):
    chat_history = data.chat_history
    message_type = data.message_type
    print(chat_history)
    try:
        if message_type == "text":
            # Xử lý tin nhắn văn bản
            text_message = data.content
            print(text_message)
            emotion = analyze_emotion_from_text(text_message)
            print(emotion)
            if not text_message:
                return {"chat_history": chat_history}
            
            # Tạo phản hồi từ Gemini
            response = model.generate_content(f"[{emotion}] {text_message}")
            generated_text = response.candidates[0].content.parts[0].text
            
            # Thêm tin nhắn vào lịch sử trò chuyện
            chat_history.append((f"🧑 Bạn: {text_message}", f"{generated_text}"))
            
        elif message_type == "audio":
            # Xử lý tin nhắn audio
            print('This is audio')
            base64_audio = data.content.get("base64_audio", "")
            if not base64_audio:
                return {"chat_history": chat_history}
            
            # Chuyển đổi base64 thành dữ liệu nhị phân
            audio_data = base64.b64decode(base64_audio)
            
            # Lưu vào file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                temp_file.write(audio_data)
                temp_input_path = temp_file.name
            
            sound = AudioSegment.from_file(temp_input_path)
    
            # Tạo file WAV mới để sử dụng với SpeechRecognition
            temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_wav_path = temp_wav_file.name
            temp_wav_file.close()
            
            # Export sang định dạng WAV PCM
            sound.export(temp_wav_path, format="wav")

            try:
                # Nhận diện giọng nói
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_wav_path) as source:
                    audio = recognizer.record(source)
                    text = recognizer.recognize_google(audio, language="vi-VN")  # Sử dụng nhận diện tiếng Việt
                # print("before reg")
                # text, emotion = recognize_text_and_emotion_from_audio(temp_wav_path)
                emotion = analyze_emotion_from_text(text)
                print(f"Emotion: {emotion}")
                print(f"Nhận diện giọng nói: {text}")
                
                # Tạo phản hồi từ Gemini
                response = model.generate_content(f"[{emotion}] {text}")
                generated_text = response.candidates[0].content.parts[0].text
                
                # Lưu audio gốc vào thư mục static (tùy chọn)
                audio_filename = f"audio_{len(chat_history)}.wav"
                audio_path = os.path.join("static", "uploads", audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                with open(audio_path, "wb") as audio_file:
                    audio_file.write(audio_data)
                
                # Thêm tin nhắn vào lịch sử trò chuyện, kèm theo đường dẫn đến file audio
                chat_history.append((
                    f"🧑 Bạn (Mic): {text}", 
                    f"{generated_text}",
                    f"/static/uploads/{audio_filename}"  # Audio URL để phát lại
                ))
                
            except sr.UnknownValueError:
                chat_history.append((
                    "🧑 Bạn (Mic): (Không nhận diện được)", 
                    "Xin lỗi, tôi không nghe rõ. Bạn có thể thử lại không?"
                ))
            finally:
                # Xóa file tạm
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
        else:
            return {"error": "Không hỗ trợ loại tin nhắn này"}
            
    except Exception as e:
        chat_history.append((f"🧑 Bạn: (Lỗi xử lý)", f"Rất tiếc, không có kết quả phù hợp được tìm thấy cho yêu cầu của bạn. Vui lòng thử lại với một câu hỏi hoặc yêu cầu khác."))
    
    # Trả về lịch sử trò chuyện mới nhất
    return {"chat_history": chat_history}

# API xử lý tin nhắn text (giữ lại cho tương thích)
@app.post("/process_text")
async def process_text(data: TextMessageData):
    chat_history = data.chat_history
    text_message = data.message
    
    if not text_message:
        return {"chat_history": chat_history}
    
    try:
        # Tạo phản hồi từ Gemini
        response = model.generate_content(text_message)
        generated_text = response.candidates[0].content.parts[0].text
        
        # Thêm tin nhắn vào lịch sử trò chuyện
        chat_history.append((f"🧑 Bạn: {text_message}", f"{generated_text}"))
        
    except Exception as e:
        chat_history.append((f"🧑 Bạn: {text_message}", f"❌ Lỗi: {str(e)}"))
    
    # Trả về lịch sử trò chuyện mới nhất
    return {"chat_history": chat_history}

# API xử lý tin nhắn audio (giữ lại cho tương thích)
@app.post("/process_audio")
async def process_audio(data: AudioData):
    chat_history = data.chat_history
    base64_audio = data.base64_audio
    
    if not base64_audio:
        return {"chat_history": chat_history}
    
    try:
        # Chuyển đổi base64 thành dữ liệu nhị phân
        audio_data = base64.b64decode(base64_audio)
        
        # Lưu vào file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data)
            tmp_filename = tmp_file.name
        
        # Lưu bản sao file audio để sau này có thể phát lại (tùy chọn)
        print("Before save")
        audio_filename = f"audio_{len(chat_history)}.wav"
        audio_path = os.path.join("static", "uploads", audio_filename)
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_data)
        
        
        # Nhận diện giọng nói
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_filename) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="vi-VN")  # Sử dụng nhận diện tiếng Việt
        
        print(f"Nhận diện giọng nói: {text}")
        
        # Tạo phản hồi từ Gemini
        response = model.generate_content(text)
        generated_text = response.candidates[0].content.parts[0].text
        
        # Thêm tin nhắn vào lịch sử trò chuyện, kèm theo đường dẫn file audio
        chat_history.append((
            f"🧑 Bạn (Mic): {text}", 
            f"{generated_text}",
            f"/static/uploads/{audio_filename}"  # Audio URL
        ))
        
    except sr.UnknownValueError:
        chat_history.append((
            "🧑 Bạn (Mic): (Không nhận diện được)", 
            "Xin lỗi, tôi không nghe rõ. Bạn có thể thử lại không?"
        ))
    except Exception as e:
        chat_history.append((
            "🧑 Bạn (Mic): (Lỗi xử lý audio)", 
            f"Rất tiếc, không có kết quả phù hợp được tìm thấy cho yêu cầu của bạn. Vui lòng thử lại với một câu hỏi hoặc yêu cầu khác."
        ))
    finally:
        # Xóa file tạm
        if 'tmp_filename' in locals() and os.path.exists(tmp_filename):
            os.remove(tmp_filename)
    
    # Trả về lịch sử trò chuyện mới nhất và URL của file audio
    return {
        "chat_history": chat_history,
        "audio_url": f"/static/uploads/{audio_filename}" if 'audio_filename' in locals() else None
    }

# Route để render index.html
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API để lấy danh sách các file audio đã lưu
@app.get("/get_audio_files")
async def get_audio_files():
    uploads_dir = os.path.join("static", "uploads")
    if not os.path.exists(uploads_dir):
        return {"audio_files": []}
    
    files = [f for f in os.listdir(uploads_dir) if f.endswith('.wav')]
    return {"audio_files": files}

# API để lấy file audio cụ thể
@app.get("/get_audio/{filename}")
async def get_audio(filename: str):
    audio_path = os.path.join("static", "uploads", filename)
    if not os.path.exists(audio_path):
        return {"error": "File không tồn tại"}
    
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
    
    return {"audio_data": base64.b64encode(audio_data).decode('utf-8')}