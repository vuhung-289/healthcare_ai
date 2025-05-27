# Installation and Setup Guide

## 1. Install Dependencies

First, you need to install all required dependencies listed in the `requirements.txt` file.

**Run the following command** in the root directory of the project:




`pip install -r requirements.txt`

This command will automatically install all the libraries required for your project.

## 2. Clone the VietTTS Repository into tts/ Directory
Next, you need to clone the VietTTS repository into a new directory called tts/. The tts/ folder does not exist in your project before this step, so you will need to create it by cloning the repository.

Run the following commands to clone the repository:

`mkdir tts`</br>
`cd tts`</br>
`git clone https://github.com/NTT123/vietTTS.git`</br>
This will clone the VietTTS repository into the tts/ directory.
## 3. Run the FastAPI Server with Uvicorn

After installing the dependencies and cloning the VietTTS repository, you can start the FastAPI server using Uvicorn.
Run the following command from the root directory of the project:

`python -m uvicorn main:app --reload`</br>
After running this command, the server will be available at:
`http://127.0.0.1:8000`</br>
