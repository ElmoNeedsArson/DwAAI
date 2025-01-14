import webview
import base64
import os
import shutil
import cv2
import threading
import mediapipe as mp
from io import BytesIO
from gradio_client import Client
import pytesseract
import easyocr
from dotenv import load_dotenv
import time
import math
import numpy as np
print("imported packages")

load_dotenv()

# Access the Hugging Face token
huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
pyTesseract_path = os.getenv('PYTESSERACT_PATH')

pytesseract.pytesseract.tesseract_cmd = pyTesseract_path

class Api:
    def __init__(self):
        self._window = None
        self.cap = None
        self.stop_camera = False
        self.stop_camBool = False
        # used when analyzing book
        self.current_book = ""
        # used when reading book
        self.activeBook = ""
        self.page = 0

    def log_message(self, message):
        print(f'console.log: {message}')  # Print to the terminal

    def set_window(self, window):
        self._window = window

    def interruptsPy(self, allow):
        print(f"interrupts choice: {allow}")
        if (allow):
            self.py_cam2()
        self.activeBook = window.evaluate_js("fetchActiveBook()")
        print(f"this is the active book: {self.activeBook}")
        window.evaluate_js(f"goToScreen('bookStart')")

    def startListening(self, next):
        # play audio
        folder_path1 = os.path.join(os.path.dirname(__file__), "books")
        folder_path2 = os.path.join(folder_path1, self.activeBook)
        files = [f for f in os.listdir(folder_path2) if os.path.isfile(os.path.join(folder_path2, f))]
        print(files)
        
        if next:
            if self.page >= len(files):
                print("end of book")
                window.evaluate_js(f"goToScreen('landingScreen')")
                window.evaluate_js(f"stopAudio()")
                print("resetting page nr")
                self.page = 0
                return
            else:
                self.page += 1
        else:
            if self.page > 1:
                self.page -= 1
            else:
                print("can't go back further")
                return
        
        # Calculate the correct file to play
        pageFromArray = self.page - 1
        fullAudioPath = os.path.join("books", self.activeBook, files[pageFromArray]).replace("\\", "/")
        print(fullAudioPath)
        
        # Play the audio file
        window.evaluate_js(f'playAudio("{fullAudioPath}")')

    def get_folders_in_folder(self, subfolder_name):
        print("folder in folder function")
        # Get the current directory of this script
        current_directory = os.path.dirname(os.path.abspath(__file__))
        
        # Construct the full path to the target subfolder
        target_directory = os.path.join(current_directory, subfolder_name)

        try:
            # Ensure the target directory exists
            if not os.path.exists(target_directory):
                print(f"Error: The directory '{target_directory}' does not exist.")
                return []

            # List all items in the target directory and filter only folders
            folders = [f for f in os.listdir(target_directory) if os.path.isdir(os.path.join(target_directory, f))]
            print(f"Found folders: {folders}")
            return folders
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

    def fetchBooks(self):
        print("fetching books")
        books = self.get_folders_in_folder("books")
        print(books)
        window.evaluate_js(f"createBookDivs({books});")

    def endBook(self):
        print(f"end book {self.current_book}")
        self.current_book = ""
        # play audio prompt book saved succesfully
        window.evaluate_js(f"goToScreen('landingScreen');")

    def nextPage(self):
        print(f"Next page of {self.current_book}")

        # starts the camera -> takes a picture -> splits picture in 2 -> stops the camera
        self.start_camera()
        img_path = self.capture_photo()
        
        print(img_path)
        self.stop_cam()
        # REPLACE WITH img_path WHEN ACTUALLY TAKING PICTURES OF BOOKS
        splitImg_paths = self.split_and_save_image("debug.jpg")

        audio_path1 = self.runModels(splitImg_paths[0], self.current_book)
        # audio indication page 1 succesfull or not
        # if not function that clears all unnecesary files and calls newBook function

        audio_path2 = self.runModels(splitImg_paths[1], self.current_book)
        # audio indication page 2 succesfull or not

        # indication code says move to next page and tap OR double tap to stop book

        # if it all goes well clear out all pictures from folders
        self.clear_folder("split_images")

    def newBook(self):
        # Creates a new folder for this book
        bookFolderName = self.create_folder("Book")
        self.current_book = bookFolderName
        
        # starts the camera -> takes a picture -> splits picture in 2 -> stops the camera
        self.start_camera()
        img_path = self.capture_photo()

        # indication code audio

        print(img_path)
        self.stop_cam()
        # REPLACE WITH img_path WHEN ACTUALLY TAKING PICTURES OF BOOKS
        splitImg_paths = self.split_and_save_image("debug.jpg")

        # feed pictures through audio generation
        
        audio_path1 = self.runModels(splitImg_paths[0], bookFolderName)
        # audio indication page 1 succesfull or not
        # if not function that clears all unnecesary files and calls newBook function

        audio_path2 = self.runModels(splitImg_paths[1], bookFolderName)
        # audio indication page 2 succesfull or not

        # indication code says move to next page and tap OR double tap to stop book

        # if it all goes well clear out all pictures from folders
        self.clear_folder("split_images")

    def start_camera(self):
        """Opens the camera and starts a video stream."""
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use CAP_DSHOW for faster initialization on Windows
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return
        print("Camera started.")
    
    def stop_cam(self):
        """Stops the camera and releases the resources."""
        if self.cap and self.cap.isOpened():
            self.stop_camBool = True
            self.cap.release()
            cv2.destroyAllWindows()
            print("Camera stopped.")
        else:
            print("Camera is not running.")

    def capture_photo(self, save_path="initial_image/captured_page.jpg"):
        """Takes a photo with the camera and saves it to the given path."""
        if self.cap is None or not self.cap.isOpened():
            print("Error: Camera is not started.")
            return
        ret, frame = self.cap.read()
        if ret:
            cv2.imwrite(save_path, frame)
            print(f"Photo saved to {save_path}")
            return save_path
        else:
            print("Error: Failed to capture photo.")

    def split_and_save_image(self, image_path, left_save_path="split_images/left_image.jpg", right_save_path="split_images/right_image.jpg"):
        """Splits the given image vertically into two equal parts and saves both parts."""
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Unable to load image from {image_path}")
            return

        # Get image dimensions
        height, width, _ = image.shape

        # Calculate midpoint
        midpoint = width // 2

        # Split the image
        left_image = image[:, :midpoint]
        right_image = image[:, midpoint:]

        # Save both images
        cv2.imwrite(left_save_path, left_image)
        cv2.imwrite(right_save_path, right_image)

        print(f"Left image saved to {left_save_path}")
        print(f"Right image saved to {right_save_path}")

        if os.path.isfile("initial_image/captured_page.jpg"):
                    os.remove("initial_image/captured_page.jpg")
                    print(f"Removed file: initial_image/captured_page.jpg")

        return [left_save_path, right_save_path]

    def create_folder(self, folder_name="books/new_folder"):
        """Creates a new folder in the 'books' directory. If the folder exists, appends a number to the name."""
        original_name = folder_name
        counter = 1
        while os.path.exists(f"books/{folder_name}"):
            folder_name = f"{original_name.split('/')[-1]}_{counter}"
            counter += 1
        os.makedirs(f"books/{folder_name}")
        print(f"Folder '{folder_name}' created successfully.")
        return folder_name

    def show_response(self, inputField):
        if not inputField:
            raise ValueError("Input field cannot be empty")
        response = {'message': inputField}
        return response

    def py_cam(self):
        print("Running Camera")
        # Initialize MediaPipe Hand solution
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils

        # Start video capture
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return

        def process_camera():
            with mp_hands.Hands(min_detection_confidence=0.4, min_tracking_confidence=0.4) as hands:
                while not self.stop_camera:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    # Flip the frame for a mirror effect
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Process frame and detect hands
                    result = hands.process(rgb_frame)

                    # Draw hand landmarks if detected and extract index finger coordinates
                    if result.multi_hand_landmarks:
                        for hand_landmarks in result.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(
                                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                            h, w, c = frame.shape
                            cx, cy = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
                            print(f"Index finger tip at: ({cx}, {cy})")

                            cv2.putText(frame, f'Index: ({cx}, {cy})', (cx, cy - 20),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                    #cv2.imshow('Finger Tracking', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop_camera = True
                        break

                self.cap.release()
                cv2.destroyAllWindows()

        # Run camera processing in a separate thread
        camera_thread = threading.Thread(target=process_camera, daemon=True)
        camera_thread.start()
    
    def py_cam2(self):
        # Initialize EasyOCR Reader
        reader = easyocr.Reader(['en'], gpu=False)

        # Initialize Mediapipe Hand Tracking
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        mp_drawing = mp.solutions.drawing_utils

        # Capture video from the camera
        cap = cv2.VideoCapture(0)

        # Helper function to calculate the angle between two points
        def calculate_angle(point1, point2):
            return math.degrees(math.atan2(point2.y - point1.y, point2.x - point1.x))

        # Helper function to detect if the hand is in a pointing position
        def is_pointing(hand_landmarks):
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
            pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

            is_index_extended = index_tip.y < index_pip.y
            are_other_fingers_folded = (
                middle_tip.y > hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y and
                ring_tip.y > hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y and
                pinky_tip.y > hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP].y
            )

            angle = calculate_angle(wrist, index_tip)

            return is_index_extended and are_other_fingers_folded and -135 < angle < -45

        def process_cam():
            # Variables to manage image capture interval
            capture_interval = 5.0  # Capture an image every second
            last_capture_time = time.time()

            # Define the width and height of the cropped image
            crop_width = 400
            crop_height = 100
            while cap.isOpened():
                success, image = cap.read()
                if not success:
                    break

                # Convert the BGR image to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image_rgb)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

                        # Convert normalized coordinates to pixel values
                        h, w, _ = image.shape
                        index_finger_pos = (int(index_finger_tip.x * w), int(index_finger_tip.y * h))

                        if is_pointing(hand_landmarks):
                            x, y = index_finger_pos

                            # Calculate rectangle coordinates
                            top_left = (max(0, x - crop_width // 2), max(0, y - crop_height))
                            bottom_right = (min(w, x + crop_width // 2), min(h, y))

                            # Draw the green rectangle
                            cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)

                            current_time = time.time()
                            if current_time - last_capture_time >= capture_interval:
                                last_capture_time = current_time

                                cropped_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

                                if cropped_image.size != 0:
                                    # Convert the cropped image to grayscale for better OCR
                                    gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)

                                    # Run EasyOCR on the cropped image
                                    text_result = reader.readtext(gray_image)

                                    # Extract and print recognized text
                                    if text_result:
                                        for (bbox, text, confidence) in text_result:
                                            print(f"Captured text: {text} (Confidence: {confidence:.2f})")

                        # Draw hand landmarks on the image
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Display the image
                cv2.imshow('Point to Capture', image)

                if cv2.waitKey(5) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()
        
        camera_thread = threading.Thread(target=process_cam, daemon=True)
        camera_thread.start()

    def clear_folder(self, folder_path):
        try:
            # List all files and subdirectories in the folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                
                # Check if it's a file and remove it
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Removed file: {filename}")
                
                # Check if it's a directory and remove it (if you want to clear subdirectories as well)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Removes the directory and its contents
                    print(f"Removed directory: {filename}")
                    
            print(f"All files and subdirectories cleared from {folder_path}")
            
        except Exception as e:
            print(f"Error clearing folder: {e}")
    
    def process_image(self, base64_image):
        window = webview.windows[0]
        try:
            # Remove the metadata prefix (e.g., "data:image/png;base64,")
            image_data = base64_image.split(',')[1]

            # Convert base64 string back to binary data
            image_binary = base64.b64decode(image_data)

            # Save the image to a file (for example, as 'uploaded_image.png')
            self.clear_folder('images')
            img_folder = "images/"
            img_path = img_folder + "analyze.png"
            with open(img_path, 'wb') as img_file:
                img_file.write(image_binary)

            audio_path = self.runModels(img_path)

            # Trigger the JS function to play audio after processing the image
            # window = webview.windows[0]  # Get the window reference
            window.evaluate_js(f'playAudio("{audio_path}");')  # Call the playAudio function in JS

            print(img_path)
            return {'message': f"Image successfully saved as {img_path}"}
        except Exception as e:
            print(f"Error processing image: {e}")
            window.evaluate_js('displayError();')
            return {'message': f"Error processing image: {str(e)}"}
    
    def runModels(self, img_path, bookFolderName):
        print(img_path)
        textfromImg = pytesseract.image_to_string(img_path)
        print(textfromImg)

        text2 = textfromImg.lower()

        print(text2)

        client = Client("yaseenuom/text-script-to-audio", hf_token=huggingface_token)
        result = client.predict(
                text=text2,
                voice="en-US-AvaMultilingualNeural - en-US (Female)",
                rate=0,
                pitch=0,
                api_name="/predict"
        )
        print(result[0])

        audio_file_path = result[0]  # Local file path
        current_folder = os.path.dirname(os.path.abspath(__file__))  # Get the script's folder

        # Ensure a unique file name by appending a number if the file already exists
        base_name = "output_audio"
        ext = ".mp3"
        output_path = os.path.join(current_folder, f"books/{bookFolderName}/{base_name}{ext}")
        counter = 1

        while os.path.exists(output_path):
            output_path = os.path.join(current_folder, f"books/{bookFolderName}/{base_name}_{counter}{ext}")
            counter += 1

        # Copy the file to the desired location
        shutil.move(audio_file_path, output_path)

        print(f"Audio saved to {output_path}")
        return output_path
        # output_path = os.path.join(current_folder, "output_audio.mp3")  # Save as "output_audio.mp3"

        # # Copy the file to the desired location
        # shutil.copy(audio_file_path, output_path)

        # print(f"Audio saved to {output_path}")
        # return output_path

    def save_picture(self, image_data):
            # Remove the base64 header from the data URL
            header, encoded = image_data.split(',', 1)
            image_bytes = base64.b64decode(encoded)

            # Save the image to the current working directory
            output_path = os.path.join(os.getcwd(), 'captured_image.png')
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            return 'Image saved to {}'.format(output_path)

if __name__ == '__main__':
    api = Api()
    #temp window
    window = webview.create_window('BlindConnection', 'index.html', js_api=api, width=400, height=700, resizable=False)
    # webview.start()
    # final window - ENABLE FOR FINAL PRODUCT
    # window = webview.create_window('BlindConnection', 'index.html', js_api=api, width=400, height=700, resizable=False, frameless=True)
    
    webview.start(debug=True)