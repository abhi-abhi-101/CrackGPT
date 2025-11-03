# CrackGPT Interview Simulator

Hey there! Welcome to the CrackGPT Interview Simulator – your friendly AI-powered buddy for practicing job interviews. This app lets you simulate interviews with AI-generated questions, record your answers, get feedback, and even analyze your body language. It's like having a personal interview coach right on your computer!

## What You Need Before Starting

- **Python 3.8 or higher** – Make sure you have Python installed. You can download it from [python.org](https://www.python.org/downloads/).
- **A computer with a webcam and microphone** – For the video and audio features.
- **API Keys** – You'll need free API keys from a few services. Don't worry, they're easy to get!

## Step 1: Get Your API Keys

You'll need these keys for the app to work. They're all free to sign up for:

1. **Gemini API Key** (for AI question generation and feedback):
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Copy it – you'll use it later

2. **HuggingFace Token** (for speech-to-text):
   - Visit [HuggingFace Settings](https://huggingface.co/settings/tokens)
   - Create a new token (set to "Read" permissions)
   - Copy the token

3. **Google Cloud API Key** (for text-to-speech):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or use an existing one
   - Enable the "Text-to-Speech" API
   - Go to "Credentials" and create an API key
   - Copy the key

4. **ElevenLabs API Key** (optional, for alternative voice):
   - Sign up at [ElevenLabs](https://elevenlabs.io/)
   - Get your API key from the dashboard

## Step 2: Download and Set Up the Project

1. **Clone the repository**:
   ```
   git clone https://github.com/abhi-abhi-101/CrackGPT-Interview-Simulator.git
   cd crackgpa_interview_app\ 2.o
   ```

2. **Create a virtual environment** (this keeps things tidy):
   ```
   python -m venv interview_env
   interview_env\Scripts\activate  # On Windows
   # Or on Mac/Linux: source interview_env/bin/activate
   ```

3. **Install the required packages**:
   ```
   pip install -r requirements.txt
   ```

## Step 3: Configure Your Settings

1. **Set up your environment variables**:
   - Open the `.env` file in a text editor
   - Add your API keys like this:
     ```
     GEMINI_API_KEY=your_gemini_key_here
     HF_TOKEN=your_huggingface_token_here
     GOOGLE_API_KEY=your_google_cloud_key_here
     ELEVENLABS_API_KEY=your_elevenlabs_key_here  # Optional
     ```
   - Save the file

## Step 4: Run the App

1. **Start the simulator**:
   ```
   streamlit run app.py
   ```

2. **Open your browser**:
   - Go to `http://localhost:8501`
   - You'll see the welcome screen!

