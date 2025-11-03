# app.py
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import tempfile
import cv2
import threading
import json 
import random # <-- NEW IMPORT
from streamlit_mic_recorder import mic_recorder
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration

# RTC Configuration for better video connectivity
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},  # Google's free STUN server
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
        {"urls": ["stun:stun3.l.google.com:19302"]},
        {"urls": ["stun:stun4.l.google.com:19302"]},
    ]
})

# helpers
from helpers import ai_helpers, pdf_helper, google_tts, transcribe
from helpers.video_helper import init_detectors, analyze_frame
from helpers.feedback_helper import generate_posture_feedback
from helpers.pdf_helper import extract_text_from_pdf

# Load environment (.env)
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")  # <- read API key from .env / env var

# --- Page setup ---
st.set_page_config(page_title="CrackGPT Interview Simulator", page_icon="🤖")
st.title("🤖 CrackGPT: AI-Powered Interview Simulator")

# --- Session state init ---
def initialize_session():
    st.session_state.clear()
    st.session_state.stage = 'initial'

if 'stage' not in st.session_state:
    initialize_session()

# --- Sidebar ---
with st.sidebar:
    # (No changes except we no longer ask for a JSON path or show the API key)
    st.header("🔑 API Setup")
    gemini_api_key = st.text_input("Gemini API Key:", type="password", value=os.getenv("GEMINI_API_KEY"))
    hf_token = st.text_input("HuggingFace Token:", type="password", value=os.getenv("HF_TOKEN"))
    # show status about Google API key (do NOT display the key)
    if google_api_key:
        st.success("Google Cloud API key loaded from environment (hidden).")
    else:
        st.warning("Google API key not found. Add `GOOGLE_API_KEY=...` to your .env or set it as an environment variable.")
    st.markdown("---")
    st.header("⚙️ Settings")
    st.session_state.disable_voice = st.checkbox("Disable voice playback", value=False)
    st.session_state.disable_video_analysis = st.checkbox("Disable posture analysis", value=False)
    st.markdown("---")
    st.header("📚 Question Bank")
    if st.button("Browse Pre-built Questions"):
        st.session_state.stage = 'browse' 
        st.rerun() 
    st.markdown("---")
    st.info("🎧 For best results, please use headphones.")
    st.markdown("---")
    st.markdown("👉 [Get Gemini key](https://aistudio.google.com/app/apikey)")
    st.markdown("👉 [Get HF token](https://huggingface.co/settings/tokens)")

def go_to(stage):
    st.session_state.stage = stage

@st.cache_data
def load_questions(filepath="questions.json"):
    # (No changes)
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: st.error(f"Error: {filepath} not found."); return []
    except json.JSONDecodeError: st.error(f"Error: Could not decode {filepath}."); return []

# --- STAGE 1: Home / Setup Choice ---
if st.session_state.stage == 'initial':
    # (No changes)
    st.header("Select Your Interview Type")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🤖 AI-Generated Interview", use_container_width=True): go_to('ai_setup')
    with col2:
        if st.button("📚 Pre-built Question Interview", use_container_width=True): go_to('prebuilt_setup')
    st.write("---")

# --- STAGE: AI Setup ---
elif st.session_state.stage == 'ai_setup':
    # (No changes)
    st.subheader("AI Interview: Enter Job Details 👇")
    if st.button("⬅️ Back to Home"): go_to('initial')
    with st.form("job_form"):
        job_title = st.text_input("Job Title", placeholder="e.g., Python Developer")
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        job_description = st.text_area("Job Description", height=200)
        resume_file = st.file_uploader("Upload Your Resume (Optional, PDF only)", type=["pdf"])
        num_questions = st.slider("Number of Questions", 3, 10, 3)
        submit = st.form_submit_button("Generate Interview Questions")
        if submit:
            if not gemini_api_key: st.error("Please add Gemini API key.")
            else:
                with st.spinner("Generating interview questions..."):
                    try:
                        resume_text = None
                        if resume_file:
                            st.info("Reading resume...")
                            resume_text, err = extract_text_from_pdf(resume_file)
                            if err: st.error(err)
                            if resume_text and len(resume_text) > 15000:
                                st.warning("Resume is long. Truncating.")
                                resume_text = resume_text[:15000]
                        st.session_state.job_details = {"title": job_title, "difficulty": difficulty}
                        st.session_state.posture_data = []
                        st.session_state.resume_text = resume_text 
                        _, questions = ai_helpers.extract_skills_and_questions(
                            gemini_key=gemini_api_key, job_title=job_title,
                            job_description=job_description, num_questions=num_questions,
                            difficulty=difficulty, resume_text=resume_text)
                        st.session_state.initial_questions = questions 
                        st.session_state.answers = [] 
                        st.session_state.current_question_index = 0
                        st.session_state.current_question_to_ask = questions[0] 
                        st.session_state.pending_followups = [] # <-- Initialize follow-up queue
                        go_to('interview')
                        st.rerun()
                    except Exception as e: st.error(str(e))

# --- STAGE: Pre-built Setup ---
elif st.session_state.stage == 'prebuilt_setup':
    # (No changes)
    st.header("🛠️ Pre-built Interview Setup")
    if st.button("⬅️ Back to Home"): go_to('initial')
    questions = load_questions()
    if questions:
        all_subjects = sorted(list(set(q['main_subject'] for q in questions)))
        all_difficulties = sorted(list(set(q.get('difficulty', 'N/A') for q in questions)))
        all_categories = sorted(list(set(cat for q in questions for cat in q.get('categories', []))))
        st.subheader("Filter Your Questions")
        col1, col2 = st.columns(2)
        with col1: sel_subject = st.selectbox("Filter by Subject", ["All"] + all_subjects)
        with col2: sel_difficulty = st.selectbox("Filter by Difficulty", ["All"] + all_difficulties)
        sel_categories = st.multiselect("Filter by Category (acts as AND)", all_categories)
        filtered_questions = questions
        if sel_subject != "All": filtered_questions = [q for q in filtered_questions if q['main_subject'] == sel_subject]
        if sel_difficulty != "All": filtered_questions = [q for q in filtered_questions if q.get('difficulty') == sel_difficulty]
        if sel_categories: filtered_questions = [q for q in filtered_questions if all(cat in q.get('categories', []) for cat in sel_categories)]
        st.write("---")
        st.markdown(f"**Found {len(filtered_questions)} questions matching your criteria.**")
        if filtered_questions:
            if st.button(f"Start Interview with these {len(filtered_questions)} Questions"):
                st.session_state.job_details = {"title": "Pre-built Interview", "difficulty": "Mixed"}
                formatted_questions = [{"question": q['question'], "type": q.get('main_subject', 'general')} for q in filtered_questions]
                st.session_state.initial_questions = formatted_questions
                st.session_state.answers = [] 
                st.session_state.current_question_index = 0
                st.session_state.current_question_to_ask = formatted_questions[0]
                st.session_state.pending_followups = [] # <-- Initialize follow-up queue
                st.session_state.posture_data = []
                go_to('interview')
                st.rerun()
            with st.expander("Preview Selected Questions"):
                for q in filtered_questions: st.markdown(f"- {q['question']}")

# --- STAGE: Browse Questions ---
elif st.session_state.stage == 'browse':
    # (No changes)
    st.header("📚 Pre-built Question Bank")
    if st.button("⬅️ Back to Interview Setup"): go_to('initial')
    questions = load_questions()
    if questions:
        all_subjects = sorted(list(set(q['main_subject'] for q in questions)))
        all_difficulties = sorted(list(set(q['difficulty'] for q in questions)))
        all_categories = sorted(list(set(cat for q in questions for cat in q['categories'])))
        col1, col2 = st.columns(2)
        with col1: sel_subject = st.selectbox("Filter by Subject", ["All"] + all_subjects)
        with col2: sel_difficulty = st.selectbox("Filter by Difficulty", ["All"] + all_difficulties)
        sel_categories = st.multiselect("Filter by Category (acts as AND)", all_categories)
        filtered_questions = questions
        if sel_subject != "All": filtered_questions = [q for q in filtered_questions if q['main_subject'] == sel_subject]
        if sel_difficulty != "All": filtered_questions = [q for q in filtered_questions if q['difficulty'] == sel_difficulty]
        if sel_categories: filtered_questions = [q for q in filtered_questions if all(cat in q['categories'] for cat in sel_categories)]
        st.write("---")
        st.markdown(f"**Showing {len(filtered_questions)} of {len(questions)} questions:**")
        for q in filtered_questions:
            with st.expander(f"**{q['question']}**"):
                st.markdown(f"**Answer:** {q['answer']}")
                st.markdown(f"**Subject:** `{q['main_subject']}` | **Difficulty:** `{q['difficulty']}`")

# --- STAGE: Interview Mode (MODIFIED) ---
elif st.session_state.stage == 'interview':
    st.subheader(f"🎤 Interview for: {st.session_state.job_details.get('title','N/A')}")
    st.warning("🎧 Remember to use headphones!", icon="💡")
    
    # Video setup (no changes)
    lock = threading.Lock()
    shared_data = {"posture_data_list": []}
    class VideoProcessor(VideoTransformerBase):
        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            if not st.session_state.get('disable_video_analysis', False):
                try:
                    data = analyze_frame(img, pose, face)
                    if data and not data.get("error"):
                        with lock: shared_data["posture_data_list"].append(data)
                except Exception as e: print(f"Error analyzing frame: {e}")
            img = cv2.flip(img, 1)
            return av.VideoFrame.from_ndarray(img, format="bgr24")
    if not st.session_state.get('disable_video_analysis', False): pose, face = init_detectors()
    webrtc_streamer(key="video", video_processor_factory=VideoProcessor, rtc_configuration=RTC_CONFIGURATION)
    with lock:
        if shared_data["posture_data_list"]:
            st.session_state.posture_data.extend(shared_data["posture_data_list"])
            shared_data["posture_data_list"].clear()
    
    st.write("---")

    # Check if we are processing an answer (transcription + follow-up generation)
    if st.session_state.get('processing_answer'):
        with st.spinner("Analyzing answer and preparing next question..."):
            try:
                raw_bytes = st.session_state.temp_audio
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(raw_bytes); tmp_path = tmp.name
                text, count, err = transcribe.transcribe_file(tmp_path)
                os.remove(tmp_path)
                if err: text, count = f"Error transcribing: {err}", 0
                
                # Save Q&A pair
                st.session_state.answers.append({
                    "question": st.session_state.current_question_to_ask,
                    "transcription": text, "filler_count": count, "audio_bytes": raw_bytes
                })
                
                # --- NEW LOGIC: Decide next step ---
                current_q_type = st.session_state.current_question_to_ask.get('type')
                
                # If there are pending follow-ups, ask the next one
                if st.session_state.pending_followups:
                    next_followup = st.session_state.pending_followups.pop(0) # Get and remove first item
                    st.session_state.current_question_to_ask = {
                        "question": next_followup, "type": "follow-up"
                    }
                
                # If it was a main question, generate follow-ups
                elif current_q_type != 'follow-up':
                    follow_ups = ai_helpers.generate_followup_questions(
                        gemini_api_key, 
                        st.session_state.current_question_to_ask['question'], 
                        text
                    )
                    st.session_state.pending_followups = follow_ups # Store the list
                    
                    if st.session_state.pending_followups:
                        # Ask the first follow-up next
                        next_followup = st.session_state.pending_followups.pop(0)
                        st.session_state.current_question_to_ask = {
                            "question": next_followup, "type": "follow-up"
                        }
                    else:
                        # No follow-ups generated, move to next main question
                        st.session_state.current_question_index += 1
                        if st.session_state.current_question_index >= len(st.session_state.initial_questions):
                            go_to('processing') # Interview over
                        else:
                            st.session_state.current_question_to_ask = st.session_state.initial_questions[st.session_state.current_question_index]
                
                # If it was the *last* follow-up, move to the next main question
                else: 
                    st.session_state.current_question_index += 1
                    if st.session_state.current_question_index >= len(st.session_state.initial_questions):
                        go_to('processing') # Interview over
                    else:
                        st.session_state.current_question_to_ask = st.session_state.initial_questions[st.session_state.current_question_index]

                st.session_state.processing_answer = False
                st.session_state.temp_audio = None
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.session_state.processing_answer = False
    
    # Display current question and record answer
    else:
        q_to_ask = st.session_state.current_question_to_ask['question']
        q_type = st.session_state.current_question_to_ask.get('type')

        if q_type == 'follow-up':
            st.warning(f"Follow-up: {q_to_ask}") # Use warning for follow-ups
        else:
            total_initial = len(st.session_state.initial_questions)
            st.info(f"Question {st.session_state.current_question_index + 1}/{total_initial}: {q_to_ask}")

        # Voice playback (changed to use google_api_key from env)
        if not st.session_state.get('disable_voice', False):
            if google_api_key:
                try:
                    audio = google_tts.tts_audio_bytes(q_to_ask, api_key=google_api_key)
                    st.audio(audio, format="audio/mpeg")
                except Exception as e:
                    st.warning(f"Google TTS failed: {e}")
            else:
                st.warning("Provide Google Cloud API key in your environment for voice playback.")
        
        # Mic recorder (use unique key based on index and type)
        audio_bytes = mic_recorder(start_prompt="🎙️ Start Answering", stop_prompt="⏹️ Stop", 
                                   key=f"rec_{st.session_state.current_question_index}_{q_type}")
        
        if audio_bytes:
            st.session_state.temp_audio = audio_bytes.get('bytes')
            st.session_state.processing_answer = True # Flag to trigger processing block
            st.rerun()

# --- STAGE: Processing Stage (Unchanged) ---
elif st.session_state.stage == 'processing':
    # (code is the same)
    st.header("⚙️ Analyzing Your Interview...")
    total_answers = len(st.session_state.answers)
    progress_bar = st.progress(0, text="Starting feedback generation...")
    status_placeholder = st.empty()
    for i, answer_data in enumerate(st.session_state.answers):
        if 'feedback_parsed' in answer_data: continue
        progress_text = f"Generating feedback for answer {i+1} of {total_answers}..."
        status_placeholder.info(progress_text)
        progress_bar.progress((i) / total_answers, text=progress_text)
        try:
            question_text = answer_data['question']['question']
            transcription = answer_data['transcription']
            filler_count = answer_data['filler_count']
            parsed, _ = ai_helpers.evaluate_answer(
                gemini_key=gemini_api_key, question=question_text, 
                transcription=transcription, filler_count=filler_count)
            st.session_state.answers[i]['feedback_parsed'] = parsed
        except Exception as e: st.session_state.answers[i]['feedback_parsed'] = {"error": f"Failed to generate feedback: {e}"}
    progress_bar.progress(1.0, text="Analysis complete!")
    status_placeholder.success("✅ All answers processed successfully!")
    if st.button("View Final Report"): go_to('feedback'); st.rerun()

# --- STAGE: Final Feedback (MODIFIED only for display) ---
elif st.session_state.stage == 'feedback':
    st.header("🎯 Final Interview Feedback")
    # Body language section (no changes)
    if not st.session_state.get('disable_video_analysis', False):
        st.subheader("Body Language Analysis")
        if st.session_state.posture_data:
            col1, col2 = st.columns(2)
            with col1:
                valid_posture = [d["posture_score"] for d in st.session_state.posture_data if d.get("posture_score") is not None]
                avg_posture = sum(valid_posture) / len(valid_posture) if valid_posture else 0
                st.metric("🧍 Avg. Posture Score", f"{round(avg_posture, 1)} / 10")
            with col2:
                valid_hair = [d["hair_score"] for d in st.session_state.posture_data if d.get("hair_score") is not None]
                avg_hair = sum(valid_hair) / len(valid_hair) if valid_hair else 0
                st.metric("💇 Avg. Hair Neatness", f"{round(avg_hair, 1)} / 10") # Note: Hair score removed in helper
            posture_feedback = generate_posture_feedback(st.session_state.posture_data)
            if posture_feedback:
                with st.expander("📝 View Detailed Posture Feedback"):
                    st.markdown(f"**Summary:** {posture_feedback['summary']}")
                    if "positives" in posture_feedback: st.markdown("**👍 What You Did Well:**"); [st.write(f"- {p}") for p in posture_feedback['positives']]
                    if "improvements" in posture_feedback: st.markdown("**🛠️ Areas for Improvement:**"); [st.write(f"- {imp}") for imp in posture_feedback['improvements']]
        else: st.info("No posture data was recorded.")
            
    st.subheader("Verbal Answer Analysis")
    main_question_counter = 0 # Keep track of main questions for numbering
    for i, data in enumerate(st.session_state.answers):
        st.write("---")
        question_text = data['question']['question']
        question_type = data['question'].get('type')
        
        # --- MODIFICATION: Display numbering based on main questions ---
        if question_type != 'follow-up':
            main_question_counter += 1
            st.info(f"Question {main_question_counter}: {question_text}")
        else:
            # Indicate it's a follow-up, maybe reference previous question number
             st.warning(f"Follow-up to Q{main_question_counter}: {question_text}") 
            
        st.text_area("Your Answer", data.get('transcription', 'No answer recorded.'), height=100, disabled=True, key=f"ans_{i}")
        
        fb = data.get('feedback_parsed', {})
        filler_count = data.get('filler_count', 0)
        if fb:
            if 'error' in fb: st.error(fb['error'])
            else:
                st.write(f"**Scores ➥** Technical: `{fb.get('technical_score','N/A')}/10` | Confidence: `{fb.get('confidence_score','N/A')}/10` | Communication: `{fb.get('communication_score','N/A')}/10` | **Filler Words:** `{filler_count}`")
                if fb.get('positives'): st.markdown("**👍 What You Did Well:**"); [st.write(f"- {p}") for p in fb['positives']]
                if fb.get('improvements'): st.markdown("**🛠️ Areas for Improvement:**"); [st.write(f"- {imp}") for imp in fb['improvements']]
                if fb.get('suggested_answer'):
                    with st.expander("💡 See Suggested Answer"): st.markdown(fb['suggested_answer'])
                        
    st.write("---")
    pdf_bytes = pdf_helper.create_pdf_report(st.session_state)
    st.download_button("📄 Download Interview Report", data=pdf_bytes, file_name="Interview_Report.pdf", mime="application/pdf")
    
    if st.button("🔁 Start New Interview"):
        initialize_session()
        st.rerun()
