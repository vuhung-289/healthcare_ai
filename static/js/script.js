const synth = window.speechSynthesis;

    function voiceControl(string) {
      let u = new SpeechSynthesisUtterance(string);
      u.lang = "en-US";
      synth.speak(u);
    }

    async function sendMessage() {
      const inputField = document.getElementById("input");
      let input = inputField.value.trim();
      input && addChat(input, "Processing...");
      inputField.value = "";

      const response = await fetch("/process_audio", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          base64_audio: "", // Temporarily empty until we have audio to process
          chat_history: [],
        }),
      });
      const result = await response.json();
      updateChatHistory(result.chat_history);
    }

    async function startRecording() {
      if (!('webkitSpeechRecognition' in window)) {
        alert("Browser doesn't support Speech Recognition");
        return;
      }

      const recognition = new webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'vi-VN'; // or 'en-US'

      recognition.start();

      recognition.onresult = async function (event) {
        const transcript = event.results[0][0].transcript;
        addChat(`You: ${transcript}`, "Listening...");
        
        // Convert the audio to base64 and send to the backend
        const base64Audio = await convertAudioToBase64(event.results[0][0].audio);
        const response = await fetch("/process_audio", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            base64_audio: base64Audio,
            chat_history: [],
          }),
        });
        
        const result = await response.json();
        updateChatHistory(result.chat_history);
      };

      recognition.onerror = function (event) {
        alert("Recording error: " + event.error);
      };
    }

    function convertAudioToBase64(audio) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(',')[1]); // base64 part only
        reader.onerror = reject;
        reader.readAsDataURL(audio);
      });
    }

    function addChat(input, product) {
      const mainDiv = document.getElementById("message-section");
      let userDiv = document.createElement("div");
      userDiv.classList.add("message");
      userDiv.innerHTML = `<span>${input}</span>`;
      mainDiv.appendChild(userDiv);

      let botDiv = document.createElement("div");
      botDiv.classList.add("message");
      botDiv.innerHTML = `<span>${product}</span>`;
      mainDiv.appendChild(botDiv);

      mainDiv.scrollTop = mainDiv.scrollHeight;
    }

    function updateChatHistory(chatHistory) {
      const mainDiv = document.getElementById("message-section");
      mainDiv.innerHTML = "";
      chatHistory.forEach(([userMsg, botMsg]) => {
        addChat(userMsg, botMsg);
      });
    }