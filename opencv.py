import cv2
import numpy as np
import os
from datetime import datetime
import threading

# Load Haar Cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Initialize video capture with optimized settings
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)

cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Face tracking for filtering small changes
previous_faces = {}
face_stability_threshold = 8  # Minimum pixel change to register as new face position

# Create directory to save screenshots
output_dir = "smile_captures"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Smile intensity tracking
smile_intensity = 0
max_smile_intensity = 0
consecutive_smile_frames = 0
smile_threshold = 90  # Approximately 3 seconds at 30fps for human verification
previous_smile_intensity = 0
smile_start_time = None  # Track when smile started

def get_smile_intensity(smile_rects):
    """
    Calculate smile intensity based on number and size of detected smiles
    Returns value between 0-100
    Amplifies small changes with 3x multiplier for sensitivity
    """
    global previous_smile_intensity
    
    if len(smile_rects) == 0:
        previous_smile_intensity = 0
        return 0
    
    # Base intensity from number of smiles detected (3x multiplier for sensitivity)
    intensity = len(smile_rects) * 40
    
    # Calculate area-based intensity with enhanced sensitivity
    area_intensity = 0
    for (x, y, w, h) in smile_rects:
        area = w * h
        # Amplify small changes by 3x
        area_intensity += (area / 50) * 3
    
    intensity += area_intensity
    
    # Boost detection if there's change from previous frame (momentum detection)
    change_factor = abs(intensity - previous_smile_intensity)
    if change_factor > 0:
        intensity += change_factor * 0.5  # Add 50% bonus for changes
    
    previous_smile_intensity = intensity
    
    # Enhance detection thresholds - even partial smiles get high scores
    if len(smile_rects) > 0:
        intensity = min(intensity, 100)
        # Ensure minimum high intensity when any smile is detected
        intensity = max(intensity, 40)
    
    return intensity

def detect_smile_curves(roi_gray, roi_color):
    """
    Detect smiles using facial curve analysis instead of just cascade
    Analyzes mouth region curvature and edge patterns indicative of smiling
    """
    if roi_gray.size == 0:
        return 0
    
    h, w = roi_gray.shape
    mouth_region_start = int(h * 0.55)  # Lower half of face
    mouth_roi = roi_gray[mouth_region_start:, :]
    
    smile_score = 0
    
    # 1. Edge detection in mouth area
    edges = cv2.Canny(mouth_roi, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    smile_score += edge_density * 40
    
    # 2. Contour analysis
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 0:
        # Look for curved patterns (smile arc)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 20:  # Filter very small contours
                epsilon = 0.02 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                # More points = more curved = likely smile
                curve_score = len(approx) * 2
                smile_score += min(curve_score, 30)
    
    # 3. Brightness differential (mouth opens when smiling)
    mouth_brightness = np.mean(mouth_roi)
    upper_roi = roi_gray[:mouth_region_start, :]
    upper_brightness = np.mean(upper_roi)
    brightness_diff = abs(mouth_brightness - upper_brightness)
    smile_score += min(brightness_diff / 5, 20)
    
    # 4. Horizontal line detection (smile line)
    edges_horizontal = cv2.Sobel(mouth_roi, cv2.CV_64F, 0, 1, ksize=5)
    horizontal_lines = np.sum(np.abs(edges_horizontal) > 30)
    smile_score += min((horizontal_lines / mouth_roi.size) * 100, 25)
    
    return min(smile_score, 60)  # Cap curve-based detection at 60

def filter_face_jitter(faces, face_id_map):
    """
    Filter out very small changes in face detection to reduce jitter
    Only keep faces that moved significantly or are new detections
    """
    global previous_faces
    
    stable_faces = []
    used_previous = set()
    
    for face in faces:
        x, y, w, h = face
        center = (x + w // 2, y + h // 2)
        
        # Check if this face matches a previous detection
        matched = False
        for prev_id, prev_face in previous_faces.items():
            if prev_id in used_previous:
                continue
            px, py, pw, ph = prev_face
            prev_center = (px + pw // 2, py + ph // 2)
            
            # Calculate distance and size difference
            distance = np.sqrt((center[0] - prev_center[0])**2 + (center[1] - prev_center[1])**2)
            size_diff = abs(w - pw) + abs(h - ph)
            
            # If close to previous position, only keep if moved significantly
            if distance < 40 and size_diff < 20:
                # Small movement - check if stable
                if distance > face_stability_threshold or size_diff > 4:
                    stable_faces.append(face)
                    used_previous.add(prev_id)
                    matched = True
                    break
            elif distance >= 40 or size_diff >= 20:
                # Large change - likely new/valid face
                stable_faces.append(face)
                used_previous.add(prev_id)
                matched = True
                break
        
        # New face detection
        if not matched:
            stable_faces.append(face)
    
    # Update previous faces
    previous_faces.clear()
    for i, face in enumerate(stable_faces):
        previous_faces[i] = face
    
    return np.array(stable_faces) if len(stable_faces) > 0 else np.array([])

def draw_face_circle(frame, face_rect):
    """Draw a circle around the face"""
    (x, y, w, h) = face_rect
    center_x = x + w // 2
    center_y = y + h // 2
    radius = max(w, h) // 2
    
    # Draw circle
    cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 3)
    return (center_x, center_y, radius)

def crop_circle_region(frame, center_x, center_y, radius):
    """Extract only the circular region with face"""
    # Create a mask for the circle
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (center_x, center_y), radius, 255, -1)
    
    # Apply mask to frame
    result = cv2.bitwise_and(frame, frame, mask=mask)
    
    # Crop to bounding box of circle
    x_min = max(0, center_x - radius)
    x_max = min(frame.shape[1], center_x + radius)
    y_min = max(0, center_y - radius)
    y_max = min(frame.shape[0], center_y + radius)
    
    cropped = result[y_min:y_max, x_min:x_max]
    return cropped

def cleanup_old_captures(output_dir, keep_latest=True):
    """
    Delete all old smile captures, keeping only the latest one
    """
    if not os.path.exists(output_dir):
        return
    
    files = [f for f in os.listdir(output_dir) if f.startswith('smile_capture_') and f.endswith('.jpg')]
    
    if len(files) <= 1:
        return
    
    # Sort by modification time
    files_with_time = [(os.path.join(output_dir, f), os.path.getmtime(os.path.join(output_dir, f))) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # Delete all except the latest
    for filepath, _ in files_with_time[1:]:
        try:
            os.remove(filepath)
            print(f"Deleted old capture: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"Failed to delete {filepath}: {e}")

def get_latest_smile_capture(output_dir):
    """
    Get the path to the latest smile capture
    Returns None if no captures exist
    """
    if not os.path.exists(output_dir):
        return None
    
    files = [f for f in os.listdir(output_dir) if f.startswith('smile_capture_') and f.endswith('.jpg')]
    
    if not files:
        return None
    
    files_with_time = [(os.path.join(output_dir, f), os.path.getmtime(os.path.join(output_dir, f))) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    return files_with_time[0][0]

def detect_smiles_threaded(roi_gray, roi_color, face_id):
    """Detect smiles using both cascade AND curve analysis for enhanced detection"""
    if roi_gray.size == 0:
        with thread_lock:
            smile_detections[face_id] = np.array([])
        return
    
    # Cascade-based detection
    smiles1 = smile_cascade.detectMultiScale(roi_gray, 1.3, 10, minSize=(15, 15))
    smiles2 = smile_cascade.detectMultiScale(roi_gray, 1.5, 8, minSize=(20, 20))
    smiles3 = smile_cascade.detectMultiScale(roi_gray, 1.8, 12, minSize=(25, 25))
    
    cascade_smiles = smiles1 if len(smiles1) > 0 else (smiles2 if len(smiles2) > 0 else smiles3)
    
    # Curve-based smile detection (enhanced detection via facial curves)
    curve_smile_score = detect_smile_curves(roi_gray, roi_color)
    
    # Combine results: if cascade found smiles, keep them; if not but curves strong, add synthetic detection
    if len(cascade_smiles) > 0:
        # Boost cascade detection if curves also detected smile
        if curve_smile_score > 50:
            # Add extra weight by duplicating some detections
            cascade_smiles = np.vstack([cascade_smiles, cascade_smiles[:len(cascade_smiles)//2]]) if len(cascade_smiles) > 1 else cascade_smiles
    elif curve_smile_score > 40:
        # Curve detected smile but cascade didn't - create synthetic detections
        h, w = roi_gray.shape
        mouth_region_start = int(h * 0.55)
        # Create detection regions based on mouth area
        cascade_smiles = np.array([[w//4, mouth_region_start, w//2, h//3]], dtype=np.int32)
    else:
        cascade_smiles = np.array([])
    
    with thread_lock:
        smile_detections[face_id] = cascade_smiles

print("Starting Face and Smile Detection")
print(f"Screenshots will be saved to: {os.path.abspath(output_dir)}")
print("Press 'q' to quit\n")

frame_count = 0
smile_detections = {}
thread_lock = threading.Lock()
smile_start_time = None

try:
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Error reading frame")
            break
        
        frame_count += 1
        frame = cv2.flip(frame, 1)
        
        small_frame = cv2.resize(frame, (0, 0), fx=0.6, fy=0.6)
        gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.equalizeHist(gray_small)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces_scale1 = face_cascade.detectMultiScale(gray_small, 1.05, 3, minSize=(25, 25), maxSize=(200, 200))
        faces_scale2 = face_cascade.detectMultiScale(gray_small, 1.15, 2, minSize=(50, 50))
        
        faces = np.vstack([faces_scale1, faces_scale2]) if len(faces_scale1) > 0 and len(faces_scale2) > 0 else faces_scale1 if len(faces_scale1) > 0 else faces_scale2
        
        if len(faces) > 0:
            faces = faces * (1/0.6)
            faces = faces.astype(int)
            face_id_map = {}
            faces = filter_face_jitter(faces, face_id_map)
        
        max_smile_in_frame = 0
        smile_detections.clear()
        
        if isinstance(faces, np.ndarray) and len(faces) > 0:
            for face in faces:
                try:
                    (x, y, w, h) = face
                except (ValueError, TypeError):
                    continue
                
                center_x, center_y, radius = draw_face_circle(frame, face)
                
                roi_gray = gray[max(0, y):min(frame.shape[0], y+h), max(0, x):min(frame.shape[1], x+w)]
                roi_color = frame[max(0, y):min(frame.shape[0], y+h), max(0, x):min(frame.shape[1], x+w)]
                
                roi_gray_enhanced = cv2.equalizeHist(roi_gray) if roi_gray.size > 0 else roi_gray
                
                face_idx = id(face)
                smile_thread = threading.Thread(target=detect_smiles_threaded, args=(roi_gray_enhanced, roi_color, face_idx))
                smile_thread.daemon = True
                smile_thread.start()
                smile_thread.join(timeout=0.2)
                
                with thread_lock:
                    smiles = smile_detections.get(face_idx, np.array([]))
                
                if not isinstance(smiles, np.ndarray) or smiles.size == 0:
                    smiles = np.array([])
                
                smile_intensity = get_smile_intensity(smiles)
                max_smile_in_frame = max(max_smile_in_frame, smile_intensity)
                
                if len(smiles) > 0:
                    for (sx, sy, sw, sh) in smiles:
                        try:
                            cv2.rectangle(roi_color, (sx, sy), (sx+sw, sy+sh), (0, 0, 255), 2)
                        except:
                            pass
                
                intensity_text = f"Smile Intensity: {int(smile_intensity)}%"
                cv2.putText(frame, intensity_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                if smile_intensity >= 98:
                    consecutive_smile_frames += 1
                    
                    # Start tracking time when smile begins
                    if smile_start_time is None:
                        smile_start_time = datetime.now()
                    
                    # Calculate elapsed time
                    elapsed_time = (datetime.now() - smile_start_time).total_seconds()
                    
                    # Display countdown timer
                    remaining_time = max(0, 3.0 - elapsed_time)
                    timer_text = f"Hold Smile: {remaining_time:.1f}s"
                    cv2.putText(frame, timer_text, (x-20, y+h+50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # Only capture after 3 seconds of sustained smile
                    if elapsed_time >= 3.0 and smile_intensity >= 98:
                        circle_crop = crop_circle_region(frame, center_x, center_y, radius)
                        
                        if circle_crop is not None and circle_crop.size > 0:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = os.path.join(output_dir, f"smile_capture_{timestamp}.jpg")
                            cv2.imwrite(filename, circle_crop)
                            print(f"[OK] Captured after 3 second human smile verification! Saved: {filename}")
                            
                            # Clean up old captures, keep only latest
                            cleanup_old_captures(output_dir)
                            
                            cv2.putText(frame, "CAPTURED!", (x-50, y+h+30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                        
                        # Reset for next capture
                        consecutive_smile_frames = 0
                        smile_start_time = None
                else:
                    consecutive_smile_frames = 0
                    smile_start_time = None  # Reset timer if smile is lost
        
        if max_smile_in_frame > 0:
            max_smile_intensity = max_smile_in_frame
        
        max_text = f"Max Intensity: {int(max_smile_intensity)}%"
        cv2.putText(frame, max_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        info_text = f"Frames: {frame_count} | Hold Max Smile for Capture"
        cv2.putText(frame, info_text, (10, frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow('Face & Smile Detection', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nExiting...")
            break

except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()

finally:
    cap.release()
    cv2.destroyAllWindows()
    print(f"\nSession ended. Check '{output_dir}' folder for captured images.")
