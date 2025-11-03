# helpers/ai_helpers.py
import json
import google.generativeai as genai
import random # <-- NEW IMPORT

def configure_gemini(key):
    genai.configure(api_key=key)

def extract_skills_and_questions(gemini_key, job_title, job_description, num_questions=5, difficulty="Medium", resume_text=None):
    # (No changes in this function)
    configure_gemini(gemini_key)
    model = genai.GenerativeModel('gemini-flash-latest') 
    skills_prompt_context = f"Here is the Job Description:\n{job_description}\n"
    if resume_text: skills_prompt_context += f"Here is the Candidate's Resume:\n{resume_text}\n"
    skills_prompt = f"""You are an expert technical interviewer. Analyze the context.\n{skills_prompt_context}\nBased *only* on the Job Description, extract key skills. Return JSON."""
    skills_resp = model.generate_content(skills_prompt)
    skills_text = skills_resp.text.strip().replace('```json', '').replace('```', '').strip()
    try: extracted_skills = json.loads(skills_text)
    except json.JSONDecodeError: extracted_skills = {"error": "Failed to parse skills JSON", "raw_text": skills_text}
    question_prompt_context = f"**Job Description:**\n{job_description}\n**Extracted Skills:**\n{json.dumps(extracted_skills)}\n"
    if resume_text: question_prompt_context += f"\n**Candidate's Resume:**\n{resume_text}\n"
    questions_prompt = f"""You are an interviewer for a {difficulty} {job_title} role. Generate {int(num_questions)} diverse questions based on:\n{question_prompt_context}\n**Strategy:** Gap Analysis, Resume Deep Dive, Standard Questions. Return JSON array with keys "question" and "type"."""
    questions_resp = model.generate_content(questions_prompt)
    questions_text = questions_resp.text.strip().replace('```json', '').replace('```', '').strip()
    try: generated_questions = json.loads(questions_text)
    except json.JSONDecodeError: generated_questions = [{"question": "Tell me about your experience.", "type": "general"}]
    return extracted_skills, generated_questions

# --- MODIFICATION: Generate 0 to 2 follow-ups ---
def generate_followup_questions(gemini_key, original_question, user_answer):
    """
    Generates 0 to 2 challenging follow-up questions based on the user's answer.
    Returns a LIST of question strings.
    """
    configure_gemini(gemini_key)
    model = genai.GenerativeModel('gemini-flash-latest') 
    
    # Decide how many follow-ups to ask (0, 1, or 2)
    num_followups = random.randint(0, 2) 
    if num_followups == 0:
        return []

    prompt = f"""
You are a sharp interviewer. The candidate was asked:
"{original_question}"

They responded:
"{user_answer}"

Ask exactly {num_followups} challenging follow-up question(s) that probe deeper into their answer, question their reasoning, or ask for specifics.
Keep the questions on the *exact same topic*. Do not change the subject.
If asking multiple, make them distinct.
Return *only* the question texts, separated by a newline character if there are multiple. Do not add numbering or commentary.
"""
    try:
        response = model.generate_content(prompt)
        # Split the response into a list of questions
        follow_ups = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
        return follow_ups[:num_followups] # Ensure we don't return more than requested
    except Exception as e:
        print(f"Follow-up question error: {e}")
        if num_followups > 0:
             return ["Can you elaborate on that?"] # Simple fallback if error occurs
        else:
             return []


def evaluate_answer(gemini_key, question, transcription, filler_count):
    configure_gemini(gemini_key)
    # --- MODIFICATION: Use non-lite model for potentially better feedback ---
    model = genai.GenerativeModel('gemini-flash-latest') 
    
    feedback_prompt = f"""
You are an expert interviewer providing feedback. Evaluate the following answer in structured JSON.
Question: "{question}"
Candidate Answer: "{transcription}"
AUDIO ANALYSIS: Candidate used ~{filler_count} filler words (um, ah, like).

Assess these keys:
- "technical_score": integer 1–10 (accuracy, depth)
- "confidence_score": integer 1–10 (Informed by filler words, fluency, hesitation)
- "communication_score": integer 1–10 (clarity, structure)
- "positives": list of short bullet points (what was done well)
- "improvements": list of specific, actionable advice
- "suggested_answer": an improved, ideal version of the answer

Return ONLY the single, clean JSON object. Ensure scores reflect quality and filler words.
"""
    resp = model.generate_content(feedback_prompt)
    fb_text = resp.text.strip().replace('```json', '').replace('```', '').strip()
    try:
        parsed = json.loads(fb_text)
    except json.JSONDecodeError:
        parsed = {"raw_feedback": fb_text}
    for k in ["technical_score", "confidence_score", "communication_score"]:
        try: parsed[k] = int(parsed.get(k))
        except (ValueError, TypeError): parsed[k] = None
    parsed.setdefault("positives", [])
    parsed.setdefault("improvements", [])
    parsed.setdefault("suggested_answer", "No suggestion available.")
    return parsed, fb_text