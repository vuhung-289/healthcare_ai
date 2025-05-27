# File Python
from vietTTS.synthesizer import synthesize

# Đọc văn bản từ file transcript.txt
with open('assets/transcript.txt', 'r', encoding='utf-8') as f:
    print("test")
    text = f.read()

# Gọi hàm synthesizer
synthesize(text, output_path='assets/infore/clip.wav', lexicon_path='assets/infore/lexicon.txt', silence_duration=0.2)
