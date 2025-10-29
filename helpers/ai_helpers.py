# helpers/ai_helpers.py
import json
import google.generativeai as genai

def configure_gemini(key):
    genai.configure(api_key=key)

def extract_skills_and_questions(gemini_key, job_title, job_description, num_questions=5, difficulty="Medium"):
    configure_gemini(gemini_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    skills_prompt = (
        f"Analyze the following job description and extract key skills:\n\n"
        f"Job Title: {job_title}\n\nDescription:\n{job_description}\n\n"
        "Categorize skills into Core Technologies, Databases, Tools, Soft Skills, etc. Return JSON."
    )
    skills_resp = model.generate_content(skills_prompt)
    skills_text = skills_resp.text.replace('```json', '').replace('```', '').strip()
    try:
        extracted_skills = json.loads(skills_text)
    except Exception:
        extracted_skills = {"raw_skills": skills_text}

    questions_prompt = (
        f"Generate {int(num_questions)} interview questions (behavioral, technical, situational) "
        f"for a {difficulty} {job_title} role with these skills: {json.dumps(extracted_skills)}. "
        "Return as a JSON list of objects with 'question' and 'type' keys."
    )
    questions_resp = model.generate_content(questions_prompt)
    questions_text = questions_resp.text.replace('```json', '').replace('```', '').strip()
    try:
        generated_questions = json.loads(questions_text)
    except Exception:
        generated_questions = [{"question": questions_text, "type": "generated"}]

    return extracted_skills, generated_questions

def evaluate_answer(gemini_key, question, transcription):
    """
    Ask Gemini to evaluate the answer and return (parsed_dict, raw_text).
    parsed_dict contains expected keys like technical_score, confidence_score, communication_score,
    positives (list), improvements (list), suggested_answer (str).
    """
    configure_gemini(gemini_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    feedback_prompt = f"""
You are an expert interview coach. Evaluate the following interview answer and return a single JSON object (no extra text).

Question: "{question}"
Answer: "{transcription}"

Return:
- technical_score: integer 1-10
- confidence_score: integer 1-10
- communication_score: integer 1-10
- positives: array of short strings (what the candidate did well)
- improvements: array of short strings (concrete actionable improvements)
- suggested_answer: a short improved phrasing or example answer (string)

Provide only one JSON object. Example:
{{"technical_score":7,"confidence_score":6,"communication_score":8,
 "positives":["Good structure","Used relevant keywords"],"improvements":["Be more specific about X"],"suggested_answer":"..."}}
"""
    resp = model.generate_content(feedback_prompt)
    fb_text = resp.text.strip()
    if fb_text.startswith("```"):
        fb_text = fb_text.strip("`").strip()

    start = fb_text.find('{')
    end = fb_text.rfind('}')
    parsed = {}
    if start != -1 and end != -1 and end > start:
        json_blob = fb_text[start:end+1]
        try:
            parsed = json.loads(json_blob)
        except Exception:
            parsed = {"raw_feedback": fb_text}
    else:
        parsed = {"raw_feedback": fb_text}

    # Normalize numeric fields
    for k in ["technical_score", "confidence_score", "communication_score"]:
        v = parsed.get(k)
        try:
            parsed[k] = int(v) if v is not None else None
        except Exception:
            parsed[k] = None

    parsed.setdefault("positives", [])
    parsed.setdefault("improvements", [])
    parsed.setdefault("suggested_answer", "")

    return parsed, fb_text
