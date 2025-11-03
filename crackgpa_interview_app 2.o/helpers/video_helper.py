# helpers/video_helper.py
import cv2
import numpy as np

try:
    import mediapipe as mp
    MP_AVAILABLE = True
    mp_pose = mp.solutions.pose
    mp_face = mp.solutions.face_detection
except ImportError:
    MP_AVAILABLE = False

def init_detectors():
    if not MP_AVAILABLE:
        return None, None
    try:
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        face = mp_face.FaceDetection(min_detection_confidence=0.5)
        return pose, face
    except Exception as e:
        print(f"Failed to initialize MediaPipe detectors: {e}")
        return None, None

def analyze_frame(frame, pose_detector, face_detector):
    """
    Input: BGR frame (numpy)
    Returns dict with posture metrics and hair heuristic.
    """
    if not MP_AVAILABLE or pose_detector is None or face_detector is None:
        return {"error": "MediaPipe not available or detectors not initialized."}

    # --- OPTIMIZATION 1: Resize frame for much faster processing ---
    target_width = 480
    h, w, _ = frame.shape
    aspect_ratio = h / w
    target_height = int(target_width * aspect_ratio)
    
    resized_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
    
    h, w, _ = resized_frame.shape
    
    # --- OPTIMIZATION 2: Process the smaller frame ---
    rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False

    posture_score = 5.0
    head_tilt = 0.0
    shoulder_diff = None
    hair_score = None

    # Pose detection
    results = pose_detector.process(rgb)
    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        
        left_sh = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_sh = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        nose = lm[mp_pose.PoseLandmark.NOSE.value]
        left_eye = lm[mp_pose.PoseLandmark.LEFT_EYE.value]
        right_eye = lm[mp_pose.PoseLandmark.RIGHT_EYE.value]

        l_sh_y = left_sh.y * h
        r_sh_y = right_sh.y * h
        shoulder_diff = abs(l_sh_y - r_sh_y)
        
        eye_dx = (left_eye.x - right_eye.x) * w
        eye_dy = (left_eye.y - right_eye.y) * h
        if eye_dx != 0:
            head_tilt = np.degrees(np.arctan2(eye_dy, eye_dx))

        shoulder_ok = shoulder_diff < (0.05 * h)
        nose_y = nose.y * h
        shoulders_mid = (l_sh_y + r_sh_y) / 2
        upright = nose_y < shoulders_mid
        
        posture_score = 8.0 if (shoulder_ok and upright) else 5.0 if shoulder_ok or upright else 3.0

    # Face detection for hair heuristic
    face_res = face_detector.process(rgb)
    if face_res.detections:
        d = face_res.detections[0]
        bbox = d.location_data.relative_bounding_box
        
        if bbox:
            x, y, bw, bh = int(bbox.xmin * w), int(bbox.ymin * h), int(bbox.width * w), int(bbox.height * h)

            top_y = max(0, y - int(0.6 * bh))
            hair_region = resized_frame[top_y:y, x:x+bw]

            if hair_region.size > 0:
                gray_hair = cv2.cvtColor(hair_region, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray_hair, 50, 150)
                edge_density = np.sum(edges) / hair_region.size
                
                hair_score = float(np.clip(10 - (edge_density * 0.5), 1, 10))
            else:
                hair_score = 5.0
    else:
        hair_score = None

    return {
        "posture_score": posture_score,
        "head_tilt_deg": round(float(head_tilt), 2),
        "shoulder_diff_px": shoulder_diff,
        "hair_score": hair_score
    }