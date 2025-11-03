# helpers/feedback_helper.py

def generate_posture_feedback(posture_data):
    """
    Analyzes a list of posture data points and returns a dictionary of feedback.
    """
    if not posture_data:
        return None

    # Calculate average metrics from the recorded data
    num_frames = len(posture_data)
    avg_score = sum(d["posture_score"] for d in posture_data if d.get("posture_score")) / num_frames
    avg_abs_tilt = sum(abs(d["head_tilt_deg"]) for d in posture_data if d.get("head_tilt_deg")) / num_frames

    feedback = {
        "summary": "",
        "positives": [],
        "improvements": []
    }

    # Generate summary and feedback based on the average score
    if avg_score >= 7.5:
        feedback["summary"] = "Excellent! Your posture was consistently strong and projected confidence."
        feedback["positives"].append("You maintained an upright and engaged posture throughout the interview.")
    elif 5 <= avg_score < 7.5:
        feedback["summary"] = "Your posture was generally good, with a solid foundation."
        feedback["positives"].append("You mostly sat upright, which helps in appearing attentive.")
    else:
        feedback["summary"] = "There's room for improvement in your posture to better convey confidence."
        feedback["improvements"].append("Focus on sitting up straight, pulling your shoulders back, and avoiding slouching.")

    # Add specific advice based on other metrics like head tilt
    if avg_abs_tilt > 12.0:
        feedback["improvements"].append("Try to keep your head level and centered. A consistent tilt can sometimes be interpreted as disinterest.")
    
    if not feedback["positives"]:
        feedback.pop("positives")
    if not feedback["improvements"]:
        feedback.pop("improvements")
        
    return feedback