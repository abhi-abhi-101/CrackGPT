# helpers/pdf_helper.py
from fpdf import FPDF
import PyPDF2
import io

def extract_text_from_pdf(pdf_file):
    # (No changes)
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in pdf_reader.pages: text += page.extract_text()
        return text, None
    except Exception as e: print(f"Error reading PDF: {e}"); return None, f"Error reading PDF file: {e}"

def create_pdf_report(interview_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'CrackGPT Interview Report', 0, 1, 'C')
    pdf.ln(10)

    def encode_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Job Title: {encode_text(interview_data.get('job_details', {}).get('title', 'N/A'))}", 0, 1)
    pdf.cell(0, 10, f"Difficulty: {encode_text(interview_data.get('job_details', {}).get('difficulty', 'N/A'))}", 0, 1)
    pdf.ln(5)

    main_question_counter = 0 # Track main question number
    for i, answer_data in enumerate(interview_data.get('answers', [])):
        pdf.set_font("Arial", 'B', 12)
        
        q_text = answer_data.get('question', {}).get('question', '')
        q_type = answer_data.get('question', {}).get('type')

        # --- MODIFICATION: Handle follow-up display in PDF ---
        if q_type != 'follow-up':
            main_question_counter += 1
            pdf.multi_cell(0, 8, f"Question {main_question_counter}: {encode_text(q_text)}")
        else:
            pdf.multi_cell(0, 8, f"Follow-up to Q{main_question_counter}: {encode_text(q_text)}")

        pdf.set_font("Arial", '', 12)
        transcription = answer_data.get('transcription', 'No answer recorded.')
        pdf.multi_cell(0, 8, f"Your Answer: {encode_text(transcription)}")

        fb = answer_data.get('feedback_parsed') or {}
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 7, "Metrics:", 0, 1) 
        pdf.set_font("Arial", '', 11)
        if fb.get("technical_score") is not None: pdf.cell(0, 6, f" - Technical: {fb.get('technical_score')}/10", 0, 1)
        if fb.get("confidence_score") is not None: pdf.cell(0, 6, f" - Confidence: {fb.get('confidence_score')}/10", 0, 1)
        if fb.get("communication_score") is not None: pdf.cell(0, 6, f" - Communication: {fb.get('communication_score')}/10", 0, 1)
        if answer_data.get("filler_count") is not None: pdf.cell(0, 6, f" - Filler Words Detected: {answer_data.get('filler_count')}", 0, 1)
        
        if fb.get("positives"):
            pdf.ln(1); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, "What you did well:", 0, 1); pdf.set_font("Arial", '', 11)
            for p in fb.get("positives", []): pdf.multi_cell(0, 6, f" - {encode_text(p)}")

        if fb.get("improvements"):
            pdf.ln(1); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, "Improvements:", 0, 1); pdf.set_font("Arial", '', 11)
            for imp in fb.get("improvements", []): pdf.multi_cell(0, 6, f" - {encode_text(imp)}")

        if fb.get("suggested_answer"):
            pdf.ln(1); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, "Suggested improved answer:", 0, 1); pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 6, encode_text(fb.get("suggested_answer")))

        pdf.ln(8)

    return pdf.output(dest='S').encode('latin-1')