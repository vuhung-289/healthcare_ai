from setuptools import setup, find_packages

setup(
    name="vietTTS",
    version="0.4.1",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "torch",
        "librosa",
        # Thêm các phụ thuộc khác của vietTTS nếu cần
    ],
)