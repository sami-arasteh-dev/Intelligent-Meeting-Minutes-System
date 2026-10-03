# Intelligent Meeting Minutes System

A professional, web-based application that automates the creation of meeting minutes. It captures audio in real-time, transcribes it using AI (Whisper), and generates structured meeting summaries using Large Language Models (LLMs).

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Technical Notes](#technical-notes)

## 🚀 Overview
This project solves the common problem of manual meeting documentation. By integrating real-time audio streaming with advanced Speech-to-Text (STT) and Natural Language Processing (NLP) capabilities, it provides a seamless workflow from recording to final document generation. It supports both online (API-based) and offline (local model) transcription modes.

## ✨ Features
- **Real-Time Recording:** Captures audio via the browser's microphone with live waveform visualization.
- **Chunked Audio Processing:** Processes audio in 5-second chunks to maintain low latency and efficient memory usage.
- **Dual Transcription Modes:**
  - **Online:** Uses a remote Whisper API for high-speed transcription.
  - **Offline:** Uses a local `whisper-large-v3` model for privacy and offline access.
- **AI Minute Generation:** Automatically generates structured meeting minutes (Summary, Decisions, Action Items) using GPT-4o.
- **Interactive Chat:** A built-in AI chatbot that can answer questions about the current meeting context.
- **Meeting Management:** Create, view, and delete meeting records with a persistent SQLite database.
- **Persian Language Support:** Optimized for Farsi transcription and minute generation.

## 🏗 Architecture & Tech Stack

### Backend
- **Framework:** Flask (Python)
- **Database:** SQLite (via `sqlite3`)
- **AI Integration:**
  - `openai` Python SDK (for LLM and STT API calls)
  - `whisper` (OpenAI's local STT model)
  - `pydub` (Audio segment handling)
- **CORS:** `flask-cors` for frontend-backend communication.

### Frontend
- **Language:** HTML5, CSS3, Vanilla JavaScript
- **Audio API:** Web Audio API (for waveform visualization), MediaRecorder API (for audio capture).
- **UI:** Custom Dark Mode interface with responsive design.

## 📦 Prerequisites
- **Python 3.8+**
- **Node.js** (Optional, if using a build step, though this project is static HTML)
- **FFmpeg:** Required by `pydub` for audio processing.
- **Whisper Model:** The first run will attempt to download the `large-v3` model if using offline mode.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If `requirements.txt` is not provided, install manually:*
   ```bash
   pip install flask flask-cors openai whisper pydub
   ```

4. **Install FFmpeg:**
   - **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/) and add to PATH.

## ⚙️ Configuration

The application configuration is located in `app.py`.

### API Keys
By default, the script uses placeholder keys. You must update the following variables in `app.py` with your actual API credentials:

```python
# STT Configuration (for Online Mode)
API_KEY = "your-stt-api-key"
STT_BASE_URL = "https://api.gapgpt.app/v1"
STT_MODEL = "gapgpt/whisper-1"

# LLM Configuration (for Minute Generation & Chat)
LLM_API_KEY = "your-llm-api-key"
LLM_BASE_URL = "https://api.gapgpt.app/v1"
LLM_MODEL = "gpt-4o"
```

### Paths
- **Uploads:** Audio files are stored in the `./uploads` directory.
- **Models:** Offline Whisper models are downloaded to `./models`.
- **Database:** SQLite database is stored in `meetings.db`.

## 🖥 Usage

1. **Start the Server:**
   ```bash
   python app.py
   ```
   The server will run on `http://127.0.0.1:5000`.

2. **Access the Interface:**
   Open your browser and navigate to `http://127.0.0.1:5000`.

3. **Create a Meeting:**
   - Fill in the meeting details (Title, Date, Subject, Participants).
   - Click **"ثبت اطلاعات جلسه"** (Register Meeting).

4. **Record Audio:**
   - Select your microphone from the dropdown.
   - Choose transcription mode: **Online**, **Offline**, or both.
   - Click **"▶ شروع ضبط"** (Start Recording).
   - Speak naturally. The text will appear in real-time.
   - Click **"⏹ پایان جلسه"** (End Meeting) when finished.

5. **Generate Minutes:**
   - Click **"✨ تولید صورتجلسه نهایی"** (Generate Final Minutes).
   - The AI will process the transcript and display the structured minutes.

6. **Chat with AI:**
   - Click the **"💬 گفتگو با هوش مصنوعی"** button at the bottom.
   - Toggle **"📋 اضافه کردن محتوای جلسه"** to allow the AI to reference the current transcript.

## 📡 API Documentation

### Endpoints

#### 1. Create Meeting
- **Endpoint:** `POST /api/meetings`
- **Body:**
  ```json
  {
    "title": "Project Review",
    "subject": "Q3 Planning",
    "participants": "Alice, Bob",
    "date": "2023-10-27"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "meeting_id": "uuid-string"
  }
  ```

#### 2. Upload Audio Chunk
- **Endpoint:** `POST /api/meetings/<meeting_id>/chunk`
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `audio`: Binary audio file (WebM).
  - `run_online`: Boolean string (`"true"`/`"false"`).
  - `run_offline`: Boolean string (`"true"`/`"false"`).
- **Response:**
  ```json
  {
    "success": true,
    "online_chunk": "Transcribed text...",
    "offline_chunk": "Transcribed text..."
  }
  ```

#### 3. Generate Minutes
- **Endpoint:** `POST /api/meetings/<meeting_id>/minutes`
- **Body:**
  ```json
  {
    "text_source": "online" // or "offline" or "both"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "minutes": "Full structured minutes text..."
  }
  ```

#### 4. Chat
- **Endpoint:** `POST /api/chat`
- **Body:**
  ```json
  {
    "messages": [
      {"role": "user", "content": "What were the main decisions?"}
    ]
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "reply": "The main decisions were..."
  }
  ```

#### 5. Get Meetings List
- **Endpoint:** `GET /api/meetings`
- **Response:** Array of meeting objects.

#### 6. Get/Delete Meeting
- **Endpoint:** `GET /api/meetings/<id>` or `DELETE /api/meetings/<id>`

## 📂 Project Structure

```text
.
├── app.py              # Main Flask application and API routes
├── index.html          # Frontend interface (HTML/CSS/JS)
├── meetings.db         # SQLite database (created on first run)
├── uploads/            # Directory for storing audio files
├── models/             # Directory for storing Whisper models
└── requirements.txt    # Python dependencies
```

## 🔧 Technical Notes

- **Threading:** The application uses `check_same_thread=False` for SQLite to handle concurrent requests safely.
- **Memory Management:** Audio chunks are processed and temporary files are deleted immediately after transcription to prevent memory leaks.
- **Offline Model:** The first time offline transcription is used, the `whisper-large-v3` model will be downloaded to the `models` directory. This may take some time depending on internet speed.
- **CORS:** Cross-Origin Resource Sharing is enabled to allow the frontend to communicate with the backend API.

## 📄 License
This project is for educational and internal use. Please ensure compliance with the licenses of the underlying libraries (Flask, Whisper, OpenAI SDK).
