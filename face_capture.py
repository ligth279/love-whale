"""
Face Capture Module
Captures user's face with smile detection for use in games
"""
import cv2
import numpy as np
import os
from datetime import datetime
import threading

class FaceCapture:
    def __init__(self, output_dir="smile_captures"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Load cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        
        # Setup camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # State tracking
        self.smile_detections = {}
        self.thread_lock = threading.Lock()
        self.previous_faces = {}
        self.face_stability_threshold = 8
        self.captured_image = None
        self.captured_path = None
    
    def get_smile_intensity(self, smile_rects):
        """Calculate smile intensity"""
        if len(smile_rects) == 0:
            return 0
        
        intensity = len(smile_rects) * 40
        for (x, y, w, h) in smile_rects:
            area = w * h
            intensity += (area / 50) * 3
        
        intensity = min(intensity, 100)
        if len(smile_rects) > 0:
            intensity = max(intensity, 40)
        
        return intensity
    
    def detect_smile_curves(self, roi_gray, roi_color):
        """Detect smiles using facial curve analysis"""
        if roi_gray.size == 0:
            return 0
        
        h, w = roi_gray.shape
        mouth_region_start = int(h * 0.55)
        mouth_roi = roi_gray[mouth_region_start:, :]
        
        smile_score = 0
        edges = cv2.Canny(mouth_roi, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        smile_score += edge_density * 40
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0:
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 20:
                    epsilon = 0.02 * cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, epsilon, True)
                    curve_score = len(approx) * 2
                    smile_score += min(curve_score, 30)
        
        mouth_brightness = np.mean(mouth_roi)
        upper_roi = roi_gray[:mouth_region_start, :]
        upper_brightness = np.mean(upper_roi)
        brightness_diff = abs(mouth_brightness - upper_brightness)
        smile_score += min(brightness_diff / 5, 20)
        
        edges_horizontal = cv2.Sobel(mouth_roi, cv2.CV_64F, 0, 1, ksize=5)
        horizontal_lines = np.sum(np.abs(edges_horizontal) > 30)
        smile_score += min((horizontal_lines / mouth_roi.size) * 100, 25)
        
        return min(smile_score, 60)
    
    def crop_circle_region(self, frame, center_x, center_y, radius):
        """Extract circular region"""
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)
        result = cv2.bitwise_and(frame, frame, mask=mask)
        
        x_min = max(0, center_x - radius)
        x_max = min(frame.shape[1], center_x + radius)
        y_min = max(0, center_y - radius)
        y_max = min(frame.shape[0], center_y + radius)
        
        return result[y_min:y_max, x_min:x_max]
    
    def detect_smiles_threaded(self, roi_gray, roi_color, face_id):
        """Detect smiles in thread"""
        if roi_gray.size == 0:
            with self.thread_lock:
                self.smile_detections[face_id] = np.array([])
            return
        
        smiles1 = self.smile_cascade.detectMultiScale(roi_gray, 1.3, 10, minSize=(15, 15))
        smiles2 = self.smile_cascade.detectMultiScale(roi_gray, 1.5, 8, minSize=(20, 20))
        smiles3 = self.smile_cascade.detectMultiScale(roi_gray, 1.8, 12, minSize=(25, 25))
        
        cascade_smiles = smiles1 if len(smiles1) > 0 else (smiles2 if len(smiles2) > 0 else smiles3)
        curve_smile_score = self.detect_smile_curves(roi_gray, roi_color)
        
        if len(cascade_smiles) > 0:
            if curve_smile_score > 50:
                cascade_smiles = np.vstack([cascade_smiles, cascade_smiles[:len(cascade_smiles)//2]]) if len(cascade_smiles) > 1 else cascade_smiles
        elif curve_smile_score > 40:
            h, w = roi_gray.shape
            mouth_region_start = int(h * 0.55)
            cascade_smiles = np.array([[w//4, mouth_region_start, w//2, h//3]], dtype=np.int32)
        else:
            cascade_smiles = np.array([])
        
        with self.thread_lock:
            self.smile_detections[face_id] = cascade_smiles
    
    def capture_face_with_smile(self, timeout=30):
        """
        Capture user's face with smile
        Returns path to captured image or None if timeout/cancelled
        """
        print("Starting Face Capture - Smile for 3 seconds to capture!")
        print(f"Press 'q' to cancel\n")
        
        frame_count = 0
        consecutive_smile_frames = 0
        smile_start_time = None
        smile_threshold = 90
        max_smile_intensity = 0
        previous_smile_intensity = 0
        
        start_time = datetime.now()
        
        try:
            while True:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    print("Capture timeout!")
                    break
                
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                frame_count += 1
                frame = cv2.flip(frame, 1)
                
                small_frame = cv2.resize(frame, (0, 0), fx=0.6, fy=0.6)
                gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                gray_small = cv2.equalizeHist(gray_small)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                faces_scale1 = self.face_cascade.detectMultiScale(gray_small, 1.05, 3, minSize=(25, 25), maxSize=(200, 200))
                faces_scale2 = self.face_cascade.detectMultiScale(gray_small, 1.15, 2, minSize=(50, 50))
                
                faces = np.vstack([faces_scale1, faces_scale2]) if len(faces_scale1) > 0 and len(faces_scale2) > 0 else faces_scale1 if len(faces_scale1) > 0 else faces_scale2
                
                if len(faces) > 0:
                    faces = faces * (1/0.6)
                    faces = faces.astype(int)
                
                self.smile_detections.clear()
                
                capture_success = False
                if isinstance(faces, np.ndarray) and len(faces) > 0:
                    for face in faces:
                        try:
                            (x, y, w, h) = face
                        except (ValueError, TypeError):
                            continue
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        radius = max(w, h) // 2
                        
                        cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 3)
                        
                        roi_gray = gray[max(0, y):min(frame.shape[0], y+h), max(0, x):min(frame.shape[1], x+w)]
                        roi_color = frame[max(0, y):min(frame.shape[0], y+h), max(0, x):min(frame.shape[1], x+w)]
                        
                        roi_gray_enhanced = cv2.equalizeHist(roi_gray) if roi_gray.size > 0 else roi_gray
                        
                        face_idx = id(face)
                        smile_thread = threading.Thread(target=self.detect_smiles_threaded, args=(roi_gray_enhanced, roi_color, face_idx))
                        smile_thread.daemon = True
                        smile_thread.start()
                        smile_thread.join(timeout=0.2)
                        
                        with self.thread_lock:
                            smiles = self.smile_detections.get(face_idx, np.array([]))
                        
                        if not isinstance(smiles, np.ndarray) or smiles.size == 0:
                            smiles = np.array([])
                        
                        smile_intensity = self.get_smile_intensity(smiles)
                        max_smile_intensity = max(max_smile_intensity, smile_intensity)
                        
                        cv2.putText(frame, f"Smile: {int(smile_intensity)}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                        
                        if smile_intensity >= 98:
                            consecutive_smile_frames += 1
                            
                            if smile_start_time is None:
                                smile_start_time = datetime.now()
                            
                            elapsed_smile = (datetime.now() - smile_start_time).total_seconds()
                            remaining = max(0, 3.0 - elapsed_smile)
                            
                            cv2.putText(frame, f"Hold: {remaining:.1f}s", (x-20, y+h+50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                            
                            if elapsed_smile >= 3.0 and smile_intensity >= 98:
                                circle_crop = self.crop_circle_region(frame, center_x, center_y, radius)
                                
                                if circle_crop is not None and circle_crop.size > 0:
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = os.path.join(self.output_dir, f"face_{timestamp}.png")
                                    cv2.imwrite(filename, circle_crop)
                                    self.captured_path = filename
                                    self.captured_image = circle_crop
                                    print(f"[OK] Captured! Saved: {filename}")
                                    cv2.putText(frame, "CAPTURED!", (x-50, y+h+30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                                    
                                    cv2.imshow('Face Capture', frame)
                                    cv2.waitKey(500)
                                    capture_success = True
                                    break
                        else:
                            consecutive_smile_frames = 0
                            smile_start_time = None
                    
                    # Exit outer loop if capture was successful
                    if capture_success:
                        break
                
                max_text = f"Max: {int(max_smile_intensity)}%"
                cv2.putText(frame, max_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                cv2.putText(frame, f"Press q to cancel", (10, frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                cv2.imshow('Face Capture', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Capture cancelled!")
                    break
        
        except Exception as e:
            print(f"Error during capture: {e}")
        
        finally:
            cv2.destroyAllWindows()
        
        return self.captured_path
    
    def release(self):
        """Release camera resources"""
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    capturer = FaceCapture()
    path = capturer.capture_face_with_smile()
    capturer.release()
