import cv2
import mediapipe as mp
import numpy as np
import time
from queue import Queue
import threading

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class SquatCounter:
    def __init__(self, socketio):
        self.socketio = socketio
        self.stop_event = threading.Event()
        self.counter = 0
        self.last_frame = None
        # Confidence tracking
        self.confidence_threshold = 0.65  # Minimum confidence for landmarks
        # State variables with hysteresis
        self.state = "up"
        self.last_rep_time = 0
        # Keep track of angles for smoothing
        self.angle_history = []
        self.history_size = 5  # Number of frames to keep for smoothing
        # Visibility tracking
        self.min_visibility = 0.5  # Minimum visibility score for landmarks

    def calculate_angle(self, a, b, c):
        """Calculate the angle between three points."""
        if None in (a, b, c):
            return None
            
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return angle if angle <= 180 else 360 - angle

    def get_body_orientation(self, landmarks):
        """Determines whether the body is in a valid squat position."""
        # Check if essential landmarks are visible
        key_points = [
            mp_pose.PoseLandmark.LEFT_SHOULDER,
            mp_pose.PoseLandmark.LEFT_HIP,
            mp_pose.PoseLandmark.LEFT_KNEE,
            mp_pose.PoseLandmark.LEFT_ANKLE,
            mp_pose.PoseLandmark.RIGHT_SHOULDER,
            mp_pose.PoseLandmark.RIGHT_HIP,
            mp_pose.PoseLandmark.RIGHT_KNEE,
            mp_pose.PoseLandmark.RIGHT_ANKLE
        ]
        
        # Check visibility of all key points
        for point in key_points:
            if landmarks[point.value].visibility < self.min_visibility:
                return "invalid"
        
        # Get positions
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Calculate body orientation
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        
        # Check if body is mostly vertical (proper squat position)
        # The y-coordinate increases as you go down in the image
        if (hip_y - shoulder_y) > 0.1:  # Shoulders should be above hips
            return "vertical"
        else:
            return "invalid"

    def get_smoothed_angle(self, new_angle):
        """Apply smoothing to angle measurements to reduce noise."""
        if new_angle is None:
            return None
            
        self.angle_history.append(new_angle)
        if len(self.angle_history) > self.history_size:
            self.angle_history.pop(0)
            
        # Return median value to filter outliers
        return np.median(self.angle_history)

    def process_frames(self):
        """Worker thread function to process frames."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open video capture")
            return

        # Reset counter and state
        self.counter = 0
        self.state = "up"
        self.last_rep_time = 0
        self.angle_history = []
        
        # Define squat angle thresholds
        squat_down_angle = 110   # Angle below which we consider a squat "down"
        squat_up_angle = 160     # Angle above which we consider a squat "up"
        
        try:
            with mp_pose.Pose(
                min_detection_confidence=0.7,  # Increased from 0.5
                min_tracking_confidence=0.7    # Increased from 0.5
            ) as pose:
                while not self.stop_event.is_set() and cap.isOpened():
                    success, image = cap.read()
                    if not success:
                        print("Error: Failed to read frame")
                        break

                    if image is None or image.size == 0:
                        continue

                    # Process image to detect pose
                    image.flags.writeable = False
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    results = pose.process(image_rgb)
                    
                    # Status reporting
                    status = "ready"
                    
                    if results.pose_landmarks:
                        landmarks = results.pose_landmarks.landmark
                        
                        # Get body orientation
                        orientation = self.get_body_orientation(landmarks)
                        
                        if orientation == "vertical":
                            # Get coordinates for both legs
                            left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                                       landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                            left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                                        landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                            left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                                         landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                            
                            right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                                        landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
                            right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                                         landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
                            right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                                          landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
                            
                            # Calculate angles for both legs
                            left_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
                            right_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
                            
                            # Use average of both legs if both are visible
                            if left_angle is not None and right_angle is not None:
                                angle = (left_angle + right_angle) / 2
                            elif left_angle is not None:
                                angle = left_angle
                            elif right_angle is not None:
                                angle = right_angle
                            else:
                                angle = None
                            
                            # Apply smoothing
                            smoothed_angle = self.get_smoothed_angle(angle)
                            
                            if smoothed_angle is not None:
                                status = f"angle:{smoothed_angle:.1f},{self.state}"
                                
                                current_time = time.time()
                                time_since_last_rep = current_time - self.last_rep_time
                                
                                # State machine logic with hysteresis
                                if self.state == "up" and smoothed_angle < squat_down_angle:
                                    self.state = "down"
                                    status = f"angle:{smoothed_angle:.1f},down"
                                    
                                elif self.state == "down" and smoothed_angle > squat_up_angle:
                                    # Ensure minimum time between reps (1 second)
                                    if time_since_last_rep > 1:
                                        self.counter += 1
                                        self.last_rep_time = current_time
                                        status = f"angle:{smoothed_angle:.1f},counted"
                                        
                                        # Emit count via socketio if available
                                        if self.socketio:
                                            self.socketio.emit("squat_count", {"count": self.counter})
                                            print(f"Squat counted: {self.counter}")
                                    self.state = "up"
                        else:
                            status = "invalid_position"
                    else:
                        status = "no_person"
                    
                    # Print status for debugging
                   # Inside the process_frames() loop, after setting the status
                    self.socketio.emit("squat_status", {"status": status})
  
                    
            print("Pose processing stopped")
        except Exception as e:
            print(f"Error in processing thread: {e}")
        finally:
            cap.release()
            print("Camera released")

    def main(self):
        """Main entry point when run directly"""
        try:
            print("Starting squat counter...")
            processing_thread = self.start()
            
            # Keep the main thread alive
            while not self.stop_event.is_set():
                time.sleep(1)
                print(f"Current count: {self.counter}")
                
        except KeyboardInterrupt:
            print("\nStopping squat counter...")
        finally:
            self.stop()
            processing_thread.join()

    def start(self):
        """Start squat counter with processing thread."""
        self.stop_event.clear()  # Make sure the event is cleared
        processing_thread = threading.Thread(target=self.process_frames)
        processing_thread.daemon = True  # Make thread exit when main program exits
        processing_thread.start()
        
        return processing_thread

    def stop(self):
        """Stop all threads."""
        print("Stopping squat counter...")
        self.stop_event.set()

if __name__ == "__main__":
    counter = SquatCounter(None)
    counter.main()



