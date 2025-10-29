# helpers/pdf_helper.py
from fpdf import FPDF

def create_pdf_report(interview_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    pdf.cell(0, 10, 'CrackGPT Interview Report', 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Job Title: {interview_data['job_details'].get('title', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Difficulty: {interview_data['job_details'].get('difficulty', 'N/A')}", 0, 1)
    pdf.ln(5)

    for i, answer_data in enumerate(interview_data['answers']):
        pdf.set_font("Arial", 'B', 12)
        q_text = interview_data['generated_questions'][i].get('question', '')
        pdf.multi_cell(0, 8, f"Question {i+1}: {q_text}")

        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 8, f"Your Answer: {answer_data.get('transcription', 'No answer recorded.')}")

        fb = answer_data.get('feedback_parsed') or {}
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 7, "Scores:", 0, 1)
        pdf.set_font("Arial", '', 11)
        if fb.get("technical_score") is not None:
            pdf.cell(0, 6, f" - Technical: {fb.get('technical_score')}/10", 0, 1)
        if fb.get("confidence_score") is not None:
            pdf.cell(0, 6, f" - Confidence: {fb.get('confidence_score')}/10", 0, 1)
        if fb.get("communication_score") is not None:
            pdf.cell(0, 6, f" - Communication: {fb.get('communication_score')}/10", 0, 1)

        if fb.get("positives"):
            pdf.ln(1)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, "What you did well:", 0, 1)
            pdf.set_font("Arial", '', 11)
            for p in fb.get("positives"):
                pdf.multi_cell(0, 6, f"  • {p}")

        if fb.get("improvements"):
            pdf.ln(1)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, "Improvements:", 0, 1)
            pdf.set_font("Arial", '', 11)
            for imp in fb.get("improvements"):
                pdf.multi_cell(0, 6, f"  • {imp}")

        if fb.get("suggested_answer"):
            pdf.ln(1)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, "Suggested improved answer:", 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 6, fb.get("suggested_answer"))

        pdf.ln(8)

    return pdf.output(dest='S').encode('latin-1')
