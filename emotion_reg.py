# voice_emotion_analyzer.py

import os
import json
import torch
import torch.nn.functional as F
import speech_recognition as sr
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

# Tên file log
LOG_FILE = 'log.json'

# Hàm ghi log
def append_log(obj):
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump([obj], f, ensure_ascii=False, indent=2)
    else:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.append(obj)
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# Load mô hình PhoBERT và Sentiment
phobert_tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
phobert_model = AutoModel.from_pretrained("vinai/phobert-base")

sentiment_tokenizer = AutoTokenizer.from_pretrained("wonrax/phobert-base-vietnamese-sentiment", use_fast=False)
sentiment_model = AutoModelForSequenceClassification.from_pretrained("wonrax/phobert-base-vietnamese-sentiment")

# Phân tích cảm xúc từ text
def analyze_emotion_from_text(text: str):
    inputs = sentiment_tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = sentiment_model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probs, dim=-1).item()
        labels = {0: "negative", 1: "positive", 2: "neutral"}
        sentiment_label = labels[predicted_class]
        confidence_score = probs[0][predicted_class].item()
        
        log_object = {
            "text": text,
            "sentiment": sentiment_label
        }
        append_log(log_object)

        return sentiment_label

# Nhận diện text từ audio và phân tích cảm xúc
def recognize_text_and_emotion_from_audio(audio_path: str):
    

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="vi-VN")  # Sử dụng nhận diện tiếng Việt
        emotion, confidence = analyze_emotion_from_text(text)
        print(text)
        return text, emotion

    except Exception as e:
        log_object = {
            "text": "Không nhận dạng được",
            "sentiment": "Lỗi",
            "error": str(e)
        }
        append_log(log_object)
        return None, None, None
