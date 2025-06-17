from flask import Flask, request, jsonify, Response
from gtts import gTTS
import tempfile
import base64
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()
genai.configure(api_key="AIzaSyAIe4WuwqXILnauHuQaJ1uFeyv1hCPRHpw")

app = Flask(__name__)
CORS(app)

# Load persona
with open("interview.txt", "r", encoding="utf-8") as f:
    persona_data = f.read()

# ========== Talker logic ==========
def talker(user_prompt):
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        prompt = f"""
You are Furkan Khan, answering as yourself.

Here is your background and personality:
{persona_data}

Now respond to this question as Furkan would: "{user_prompt}"

If the answer is not in the profile, respond thoughtfully in his tone (concise, practical, and honest).
"""
        response = model.generate_content(prompt)
        return response.text or "No response from Gemini."
    except Exception as e:
        print("❌ Gemini Error:", e)
        return "Gemini failed to generate content."


# ========== Routes ==========

@app.route('/')
def serve_index():
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Furkan Voice Bot</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      text-align: center;
      padding-top: 60px;
      background: #f5f7fa;
    }

    h2 {
      color: #333;
    }

    button {
      padding: 10px 20px;
      font-size: 16px;
      cursor: pointer;
      margin-bottom: 20px;
      background-color: #4CAF50;
      color: white;
      border: none;
      border-radius: 6px;
    }

    #loader {
      display: none;
      margin-top: 20px;
      font-weight: bold;
    }

    p {
      font-size: 18px;
    }

    audio {
      margin-top: 15px;
    }
  </style>
</head>
<body>
  <h2>🎤 Ask something to Furkan</h2>
  <button id="startButton">🎙️ Start Voice Input</button>
  <div id="loader">⏳ Furkan is thinking...</div>

  <p><strong>You asked:</strong> <span id="userText"></span></p>
  <p><strong>Furkan says:</strong> <span id="botReply"></span></p>
  <audio id="botAudio" controls></audio>

<script>
  const startButton = document.getElementById('startButton');
  const userTextSpan = document.getElementById('userText');
  const botReplySpan = document.getElementById('botReply');
  const botAudio = document.getElementById('botAudio');
  const loader = document.getElementById('loader');

  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = 'en-US';

  let isRecognizing = false;
  let recognitionTimeout;

  recognition.onstart = () => {
    isRecognizing = true;
    startButton.textContent = '🎧 Listening...';
    userTextSpan.textContent = '';
    botReplySpan.textContent = '';
    botAudio.src = '';
    loader.style.display = 'none';
    recognitionTimeout = setTimeout(() => {
      recognition.stop();
    }, 5000);
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userTextSpan.textContent = transcript;
    askFurkan(transcript);
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    isRecognizing = false;
    clearTimeout(recognitionTimeout);
    recognition.abort();
    startButton.textContent = '🎙️ Start Voice Input';
  };

  recognition.onend = () => {
    isRecognizing = false;
    clearTimeout(recognitionTimeout);
    startButton.textContent = '🎙️ Start Voice Input';
  };

  startButton.addEventListener('click', () => {
    if (!isRecognizing) {
      recognition.start();
    } else {
      recognition.stop();
    }
  });

  async function askFurkan(question) {
    loader.style.display = 'block';
    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question })
      });

      const data = await res.json();
      botReplySpan.textContent = data.reply;
      loader.style.display = 'none';

      if (data.audio_base64) {
        botAudio.src = 'data:audio/mp3;base64,' + data.audio_base64;
        botAudio.play();
      }
    } catch (err) {
      console.error("❌ Error fetching from server:", err);
      loader.textContent = '❌ Failed to get response from server.';
    }
  }
</script>
</body>
</html>
"""
    return Response(html, mimetype='text/html')


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({"error": "No message received"}), 400

    response_text = talker(user_message)

    # Convert response to speech
    tts = gTTS(response_text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tts.save(f.name)
        f.seek(0)
        audio_base64 = base64.b64encode(f.read()).decode()

    return jsonify({
        "reply": response_text,
        "audio_base64": audio_base64
    })


# Start app
if __name__ == '__main__':
    app.run(debug=True)
