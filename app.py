# app.py
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import streamlit as st


import json
import tempfile
import traceback


os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from streamlit_mic_recorder import mic_recorder

# helpers
from helpers import ai_helpers, pdf_helper, eleven, transcribe

# load env if present
from dotenv import load_dotenv
load_dotenv()

# --- Page config ---
st.set_page_config(page_title="CrackGPT Interview Simulator", page_icon="🤖")

# --- Session state init ---
if 'stage' not in st.session_state:
    st.session_state.stage = 'initial'
if 'job_details' not in st.session_state:
    st.session_state.job_details = {}
if 'generated_questions' not in st.session_state:
    st.session_state.generated_questions = []
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'answers' not in st.session_state:
    st.session_state.answers = []
# ElevenLabs voices cache
if 'eleven_voices' not in st.session_state:
    st.session_state.eleven_voices = []
if 'eleven_voices_key' not in st.session_state:
    st.session_state.eleven_voices_key = None

def go_to_stage(stage):
    st.session_state.stage = stage

# --- Sidebar: API keys + Voices ---
with st.sidebar:
    st.title("🔑 API Key Setup")
    gemini_api_key = st.text_input("Google Gemini API Key:", type="password", value=os.getenv("GEMINI_API_KEY"))
    elevenlabs_api_key = st.text_input("ElevenLabs API Key:", type="password", value=os.getenv("ELEVENLABS_API_KEY"))
    hf_token = st.text_input("Hugging Face Token:", type="password", value=os.getenv("HF_TOKEN"))
    st.markdown("👉 [Get Google API key](https://aistudio.google.com/app/apikey)")
    st.markdown("👉 [Get ElevenLabs API key](https://elevenlabs.io/)")
    st.markdown("👉 [Get Hugging Face token](https://huggingface.co/settings/tokens)")

    # Fetch voices (only when key changes)
    if elevenlabs_api_key:
        if st.session_state.eleven_voices_key != elevenlabs_api_key or not st.session_state.eleven_voices:
            try:
                voices = eleven.fetch_elevenlabs_voices(elevenlabs_api_key)
                st.session_state.eleven_voices = voices
                st.session_state.eleven_voices_key = elevenlabs_api_key
            except Exception:
                st.session_state.eleven_voices = []
        voices = st.session_state.eleven_voices or []
        if voices:
            display = []
            id_map = {}
            for v in voices:
                vid = v.get("voice_id") or v.get("id") or v.get("voiceId") or ""
                name = v.get("name") or v.get("voice_name") or vid or "unknown"
                disp = f"{name} ({vid})"
                display.append(disp)
                id_map[disp] = vid
            chosen_disp = st.selectbox("Choose ElevenLabs voice:", display, index=0)
            st.session_state.eleven_voice_id = id_map.get(chosen_disp)
        else:
            st.info("No voices found for this ElevenLabs key (or fetch failed).")
            st.session_state.eleven_voice_id = None
    else:
        st.caption("Add your ElevenLabs API key to fetch TTS voices.")
        st.session_state.eleven_voice_id = None

# --- Main App UI ---
st.title("🤖 CrackGPT: AI-Powered Interview Simulator")

# STAGE 1: Job input
if st.session_state.stage == 'initial':
    st.write("Enter the details of the job you want to practice for.")
    with st.form("job_input_form"):
        job_title = st.text_input("Job Profile / Title", placeholder="e.g., Senior Python Developer")
        difficulty = st.selectbox("Select Difficulty Level", options=["Easy", "Medium", "Hard"])
        job_description = st.text_area("Job Description", placeholder="Paste the full job description here.", height=300)
        num_questions = st.number_input("Number of questions to generate:", min_value=3, max_value=15, value=5)
        submitted = st.form_submit_button("Generate Interview Questions")

        if submitted:
            if not gemini_api_key:
                st.sidebar.error("Please enter your Gemini API key!")
            elif not job_title or not job_description:
                st.error("Please fill out all job details.")
            else:
                with st.spinner("Analyzing job and generating questions... 🧠"):
                    try:
                        skills, generated_questions = ai_helpers.extract_skills_and_questions(
                            gemini_key=gemini_api_key,
                            job_title=job_title,
                            job_description=job_description,
                            num_questions=int(num_questions),
                            difficulty=difficulty
                        )
                        st.session_state.job_details = {"title": job_title, "difficulty": difficulty, "skills": skills}
                        st.session_state.generated_questions = generated_questions
                        st.session_state.answers = [{} for _ in generated_questions]
                        go_to_stage('interview')
                    except Exception as e:
                        st.error(f"Error generating questions: {e}")
                        st.text(traceback.format_exc())

# STAGE 2: Interview simulation
elif st.session_state.stage == 'interview':
    st.subheader(f"Interview for: **{st.session_state.job_details.get('title','(unknown)')}**")
    st.write("---")

    q_index = st.session_state.current_question_index
    total_questions = len(st.session_state.generated_questions)
    if total_questions == 0:
        st.warning("No questions available. Start again.")
        if st.button("Back to Start"):
            go_to_stage('initial')
    else:
        current_question = st.session_state.generated_questions[q_index]
        st.info(f"**Question {q_index + 1}/{total_questions}:** ({current_question.get('type','')})")
        st.markdown(f"### {current_question.get('question','(no question)')}")

        # Listen to question via ElevenLabs (optional)
        if elevenlabs_api_key:
            if st.button("▶️ Listen to Question"):
                try:
                    voice_id = st.session_state.get("eleven_voice_id") or "alloy"
                    audio_bytes = eleven.tts_audio_bytes(elevenlabs_api_key, voice_id, current_question.get('question',''))
                    st.audio(audio_bytes, format="audio/wav")
                except Exception as e:
                    st.error(f"ElevenLabs TTS failed: {e}")

        st.write("---")
        st.write("Your Answer:")

        audio_bytes = mic_recorder(start_prompt="🔴 Start Recording", stop_prompt="⏹️ Stop Recording", key=f'recorder-{q_index}')

        if audio_bytes:
            with st.spinner("Transcribing your answer... ✍️"):
                tmp_file_path = None
                try:
                    raw_bytes = None
                    if isinstance(audio_bytes, dict) and 'bytes' in audio_bytes:
                        raw_bytes = audio_bytes['bytes']
                    elif isinstance(audio_bytes, (bytes, bytearray)):
                        raw_bytes = bytes(audio_bytes)
                    else:
                        try:
                            raw_bytes = audio_bytes.get('bytes')
                        except Exception:
                            raw_bytes = None

                    if not raw_bytes:
                        st.error("Recorder returned no audio bytes.")
                    else:
                        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                        tmp_file_path = tmp.name
                        tmp.write(raw_bytes)
                        tmp.flush()
                        tmp.close()

                        transcription, err = transcribe.transcribe_file(tmp_file_path, hf_token)
                        if transcription:
                            st.session_state.answers[q_index]['transcription'] = transcription
                        else:
                            st.error("Transcription failed.")
                            if err:
                                st.text(err)

                finally:
                    try:
                        if tmp_file_path and os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)
                    except Exception:
                        pass

        # show transcription, and ask for feedback
        if 'transcription' in st.session_state.answers[q_index]:
            st.text_area("Your Transcribed Answer:", value=st.session_state.answers[q_index]['transcription'], height=150, disabled=True)

            if st.button("Get Feedback", key=f"feedback-{q_index}"):
                with st.spinner("Our AI is evaluating your answer... 🤔"):
                    try:
                        if not gemini_api_key:
                            st.sidebar.error("Please enter your Gemini API key to generate feedback.")
                        else:
                            parsed, raw = ai_helpers.evaluate_answer(
                                gemini_key=gemini_api_key,
                                question=current_question.get('question',''),
                                transcription=st.session_state.answers[q_index]['transcription']
                            )
                            st.session_state.answers[q_index]['feedback_parsed'] = parsed
                            st.session_state.answers[q_index]['feedback_raw'] = raw
                    except Exception as e:
                        st.error(f"Feedback generation failed: {e}")
                        st.text(traceback.format_exc())

        # display parsed feedback
        fb_parsed = st.session_state.answers[q_index].get('feedback_parsed')
        if fb_parsed:
            st.write("---")
            st.success("AI Feedback (scored):")

            ts = fb_parsed.get("technical_score")
            cs = fb_parsed.get("confidence_score")
            comms = fb_parsed.get("communication_score")

            cols = st.columns(3)
            if ts is not None:
                cols[0].metric("Technical (1-10)", ts)
                cols[0].progress(min(max(int(ts)*10, 0), 100))
            else:
                cols[0].info("Technical: N/A")

            if cs is not None:
                cols[1].metric("Confidence (1-10)", cs)
                cols[1].progress(min(max(int(cs)*10, 0), 100))
            else:
                cols[1].info("Confidence: N/A")

            if comms is not None:
                cols[2].metric("Communication (1-10)", comms)
                cols[2].progress(min(max(int(comms)*10, 0), 100))
            else:
                cols[2].info("Communication: N/A")

            st.markdown("**What you did well:**")
            if fb_parsed.get("positives"):
                for p in fb_parsed.get("positives"):
                    st.write(f"- {p}")
            else:
                st.write("- (No positives provided)")

            st.markdown("**Concrete improvements:**")
            if fb_parsed.get("improvements"):
                for imp in fb_parsed.get("improvements"):
                    st.write(f"- {imp}")
            else:
                st.write("- (No improvements provided)")

            if fb_parsed.get("suggested_answer"):
                st.markdown("**Suggested improved phrasing:**")
                st.code(fb_parsed.get("suggested_answer"))

        # Navigation
        st.write("---")
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if q_index > 0 and st.button("⬅️ Previous Question"):
                st.session_state.current_question_index -= 1
        with col3:
            if q_index < total_questions-1 and st.button("Next Question ➡️"):
                st.session_state.current_question_index += 1
            elif q_index == total_questions-1 and st.button("Finish Interview ✅"):
                go_to_stage('feedback')

# STAGE 3: Feedback summary + PDF
elif st.session_state.stage == 'feedback':
    st.success("🎉 Interview Complete! 🎉")
    st.balloons()
    st.subheader("Here is a summary of your performance:")

    tech_scores, conf_scores, comm_scores = [], [], []

    for i, answer_data in enumerate(st.session_state.answers):
        st.write("---")
        st.info(f"**Question {i+1}:** {st.session_state.generated_questions[i].get('question','')}")
        st.markdown(f"**Your Answer (transcribed):** *{answer_data.get('transcription','No answer recorded.')}*")

        fb = answer_data.get('feedback_parsed') or {}
        if fb:
            ts = fb.get("technical_score")
            cs = fb.get("confidence_score")
            cms = fb.get("communication_score")
            if ts is not None: tech_scores.append(int(ts))
            if cs is not None: conf_scores.append(int(cs))
            if cms is not None: comm_scores.append(int(cms))

            st.success("**AI Feedback (scored):**")
            cols = st.columns(3)
            cols[0].metric("Technical", ts if ts is not None else "N/A")
            cols[1].metric("Confidence", cs if cs is not None else "N/A")
            cols[2].metric("Communication", cms if cms is not None else "N/A")

            st.markdown("**What you did well:**")
            if fb.get("positives"):
                for p in fb.get("positives"):
                    st.write(f"- {p}")
            else:
                st.write("- (No positives provided)")

            st.markdown("**Concrete improvements:**")
            if fb.get("improvements"):
                for imp in fb.get("improvements"):
                    st.write(f"- {imp}")
            else:
                st.write("- (No improvements provided)")

            if fb.get("suggested_answer"):
                st.markdown("**Suggested improved phrasing:**")
                st.code(fb.get("suggested_answer"))
        else:
            st.write("_No structured feedback for this question._")

    def avg(lst):
        return round(sum(lst)/len(lst),1) if lst else None

    st.write("---")
    st.subheader("Overall scores (averaged across answered questions)")
    a_tech = avg(tech_scores)
    a_conf = avg(conf_scores)
    a_comm = avg(comm_scores)

    cols = st.columns(3)
    cols[0].metric("Avg Technical (1-10)", a_tech if a_tech is not None else "N/A")
    cols[1].metric("Avg Confidence (1-10)", a_conf if a_conf is not None else "N/A")
    cols[2].metric("Avg Communication (1-10)", a_comm if a_comm is not None else "N/A")

    st.write("---")
    st.subheader("Download Your Report")
    pdf_bytes = pdf_helper.create_pdf_report(st.session_state)
    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_bytes,
        file_name=f"interview_report_{st.session_state.job_details.get('title','report').replace(' ','_')}.pdf",
        mime="application/pdf"
    )

    if st.button("Start a New Interview"):
        st.session_state.clear()
        st.experimental_rerun()
