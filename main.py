__version__ = "1.0"

import webview
import base64
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import shutil
import cv2
import threading
import mediapipe as mp
from gradio_client import Client
import pytesseract
import easyocr
from dotenv import load_dotenv
import time
import math
import numpy as np
from queue import Queue
import google.generativeai as genai
print("imported packages")

load_dotenv()

# Access the Hugging Face token and the pyTesseract path
huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
pyTesseract_path = os.getenv('PYTESSERACT_PATH')

# Establishing the google api
google_key = os.getenv('GENAI_KEY')
genai.configure(api_key=google_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize the pyTesseract module
pytesseract.pytesseract.tesseract_cmd = pyTesseract_path

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'], gpu=False)

class Api:
    def __init__(self):
        self._window = None
        self.cap = None
        self.stop_camera = False
        self.stop_camBool = False
        # used when analyzing book
        self.current_book = "" 
        self.analyze_page = 0
        # used when reading book
        self.activeBook = ""
        self.page = 1
        self.pageIndex = 0
        self.camNR = 1
        self.stop_thread = False
        self.camType = cv2.CAP_DSHOW # or cv2.CAP_ANY or cv2.CAP_DSHOW or cv2.CAP_MSMF
        self.processing_queue = Queue()
    
    def set_window(self, window):
        self._window = window

    def setThreadStop(self):
        self.stop_thread = True

    def interruptsPy(self, allow):
        print(f"interrupts choice: {allow}")
        if (allow):
            self.stop_thread = False
            self.py_cam2()
        self.activeBook = window.evaluate_js("fetchActiveBook()")
        print(f"this is the active book: {self.activeBook}")
        window.evaluate_js(f"playAudio('Audio/Interactivemode_1.mp3','Audio/PlayAudio_1.mp3')")
        window.evaluate_js(f"goToScreen('bookStart')")

    def playPreviousAudio(self):
        folder_path2 = os.path.join(os.path.dirname(__file__), "books", self.activeBook)
        folder_path3 = os.path.join(folder_path2, f"page{self.page}")

        files = [f for f in os.listdir(folder_path3) if os.path.isfile(os.path.join(folder_path3, f))]
        if self.pageIndex > 1:
            self.pageIndex -= 2  # Go to the previous audio file
            print(f"Playing previous audio on page {self.page}, index {self.pageIndex}")
            self.startListening(next=True)
        elif self.page > 1:
            self.page -= 1
            prev_folder_path = os.path.join(folder_path2, f"page{self.page}")
            prev_files = [f for f in os.listdir(prev_folder_path) if os.path.isfile(os.path.join(prev_folder_path, f))]
            if prev_files:
                self.pageIndex = len(prev_files) - 1
                print(f"Playing last audio on page {self.page}, index {self.pageIndex}")
                self.startListening(next=True)
        else:
            print("No previous audio to play")

    def startListening(self, next):
        # play audio
        folder_path1 = os.path.join(os.path.dirname(__file__), "books")
        folder_path2 = os.path.join(folder_path1, self.activeBook)
        folder_path3 = os.path.join(folder_path2, f"page{self.page}")

        files = [f for f in os.listdir(folder_path3) if os.path.isfile(os.path.join(folder_path3, f))]
        directories = [d for d in os.listdir(folder_path2) if os.path.isdir(os.path.join(folder_path2, d))]
        nrOfAudioFilesPage = len(files)
        print(files)
        print(f"Nr: {nrOfAudioFilesPage}")
        print(f"pagindex: {self.pageIndex}")

        print(f"Page: {self.page}")
        print(f"Nr_Dir: {len(directories)}")

        def playCorrectAudio():
            # Calculate the correct file to play
            fullAudioPath = os.path.join("books", self.activeBook, f"page{self.page}", files[self.pageIndex]).replace("\\", "/")
            print(fullAudioPath)
            
            # Play the audio file
            window.evaluate_js(f'playAudio("{fullAudioPath}")')

        if next:
            # user clicks the next button -> navigating to next page or ending book
            if self.pageIndex < nrOfAudioFilesPage:
                print("play audio")
                print(f"Play page: {self.page} index: {self.pageIndex}")
                playCorrectAudio()
                self.pageIndex += 1
                # play audio of index and page
            elif self.pageIndex >= nrOfAudioFilesPage:
                print("played all audio files from this page")
                self.page += 1
                if self.page > len(directories):
                    print("book finished")
                    window.evaluate_js(f"goToScreen('landingScreen')")
                    window.evaluate_js(f"stopAudio()")
                    window.evaluate_js(f"playAudio('Audio/BookFinished_1.mp3')")
                    self.stop_cam()
                    self.stop_thread = True
                    self.page = 1
                    self.pageIndex = 0
                else:
                    self.pageIndex = 0
                    print(f"Play page: {self.page} index: {self.pageIndex}")
                    playCorrectAudio()
                    self.pageIndex += 1
                    # play audio of index and page
        else:
            print("user wants to turn back")
            # play current file again
            if self.pageIndex > 0:
                self.pageIndex -= 1
                print(f"Play page: {self.page} index: {self.pageIndex}")
                playCorrectAudio()
                self.pageIndex += 1
            else:
                if self.page > 1:
                    self.page -= 1
                    folder_path3 = os.path.join(folder_path2, f"page{self.page}")
                    files = [f for f in os.listdir(folder_path3) if os.path.isfile(os.path.join(folder_path3, f))]
                    self.pageIndex = len(files)-1
                    print(f"Play page: {self.page} index: {self.pageIndex}")
                    playCorrectAudio()
                    self.pageIndex += 0
                    self.page += 1
                else:
                    print("Cant go back further")

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
        image = cv2.imread(img_path)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply contrast enhancement using Histogram Equalization
        enhanced = cv2.equalizeHist(gray)

        # Save the processed image
        cv2.imwrite(img_path, enhanced)
        splitImg_paths = self.split_and_save_image(img_path)

        self.analyze_page = self.analyze_page + 1
        audio_path1 = self.runModels(splitImg_paths[0], self.current_book, self.analyze_page)
        window.evaluate_js(f"playAudio('Audio/Scanning_1.mp3')")

        # audio indication page 1 succesfull or not
        # if not function that clears all unnecesary files and calls newBook function
        if(audio_path1 == None):
           return # better error handle
        else:
            self.analyze_page = self.analyze_page + 1
            audio_path2 = self.runModels(splitImg_paths[1], self.current_book, self.analyze_page)
        # audio indication page 2 succesfull or not
        if(audio_path2 == None):
           return # better error handle
        elif(audio_path2 != None):
            window.evaluate_js(f"playAudio('Audio/SucessfulScan_1.mp3')")

        # indication code says move to next page and tap OR double tap to stop book

        # if it all goes well clear out all pictures from folders
        # self.clear_folder("split_images")

    def newBook(self):
        self.analyze_page = 0
        # Creates a new folder for this book
        bookFolderName = self.create_folder("Book")
        self.current_book = bookFolderName

    def start_camera(self):
        """Opens the camera and starts a video stream."""
        self.cap = cv2.VideoCapture(self.camNR, self.camType)  # Use CAP_DSHOW for faster initialization on Windows
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
        self.cap = cv2.VideoCapture(self.camNR, self.camType)
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
    
    def txtIntoAudio(self, txt):
        print(f"Text turned into audio: {txt}")
        if(txt.strip() == ""):
            print("No text detected")
            return 
        else:
            text2 = txt.strip()
            print("text Detected")

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
            os.remove("wordPopUpAudio/txt.mp3")
            output_path = os.path.join(current_folder, "wordPopUpAudio/txt.mp3")

            # Copy the file to the desired location
            shutil.move(audio_file_path, output_path)

            print(f"Audio saved to {output_path}")
            return output_path
        
    def process_image_worker(self):
        """Worker thread for processing images and running OCR."""
        while True:
            cropped_image, image_index = self.processing_queue.get()
            if cropped_image is None:
                break

            # Convert the cropped image to grayscale for better OCR
            gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)

            # Scale the image up
            scale_percent = 200  # Increase size by 200%
            width = int(gray_image.shape[1] * scale_percent / 100)
            height = int(gray_image.shape[0] * scale_percent / 100)
            scaled_image = cv2.resize(gray_image, (width, height), interpolation=cv2.INTER_CUBIC)

            # Sharpen the image using a kernel
            sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(scaled_image, -1, sharpen_kernel)

            # Enhance contrast using CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(sharpened)

            # Save the processed image
            cv2.imwrite(f'word.jpg', enhanced)

            # Run EasyOCR on the processed image
            text_result = reader.readtext(enhanced)

            # Extract and print recognized text
            if text_result:
                for (bbox, text, confidence) in text_result:
                    print(f"Captured text: {text} (Confidence: {confidence:.2f})")
                    if confidence > 0.64:
                        print(f"Captured text: {text} (Confidence: {confidence:.2f})")
                        def get_center_word(text):
                            words = text.split()
                            # Calculate the visual center based on character widths including spaces
                            total_length = sum(len(word) + 1 for word in words) - 1  # -1 to remove the last extra space
                            center_pos = total_length // 2

                            # Find the word that covers the center position
                            current_pos = 0
                            for word in words:
                                current_pos += len(word) + 1  # Add word length and one space
                                if current_pos > center_pos:
                                    return word
                        center = get_center_word(text)
                        print(f"Center word: {center}")
                        wordPath = self.txtIntoAudio(text)
                        trimmed_path = os.path.join(os.path.basename(os.path.dirname(wordPath)), os.path.basename(wordPath))
                        trimmed_path = trimmed_path.replace("\\", "/")
                        print(f"Path to word audio: {trimmed_path}")
                        window.evaluate_js(f"setPopUpWordConfidence('{trimmed_path}')")
                        # Play a ding! sound
                        window.evaluate_js(f"playOverAudio('Audio/ding.mp3')")
                        window.evaluate_js(f"goToScreen('popUpWord')")
    
    def py_cam2(self):

        # Initialize Mediapipe Hand Tracking
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        mp_drawing = mp.solutions.drawing_utils

        # Capture video from the camera
        cap = cv2.VideoCapture(self.camNR, self.camType)

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
            crop_width = 60
            crop_height = 30
            image_index = 0
            while cap.isOpened() and not self.stop_thread:
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
                            vertical_offset = 10
                            top_left = (max(0, x - crop_width // 2), max(0, y - crop_height - vertical_offset))
                            bottom_right = (min(w, x + crop_width // 2), min(h, y - vertical_offset))

                            # Draw the green rectangle
                            cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)

                            current_time = time.time()
                            if current_time - last_capture_time >= capture_interval:
                                print("5 seconds passed, running again")
                                last_capture_time = current_time

                                cropped_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
                                if cropped_image.size != 0:
                                    # Add the image to the processing queue
                                    self.processing_queue.put((cropped_image, image_index))
                                    image_index += 1

                                # cropped_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

                                # if cropped_image.size != 0:
                                #     # Convert the cropped image to grayscale for better OCR
                                #     gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
                                #     # STEP 1: Scale the image up
                                #     scale_percent = 200  # Increase size by 200% (adjust as needed)
                                #     width = int(image.shape[1] * scale_percent / 100)
                                #     height = int(image.shape[0] * scale_percent / 100)
                                #     scaled_image = cv2.resize(gray_image, (width, height), interpolation=cv2.INTER_CUBIC)

                                #     # STEP 2: Sharpen the image using a kernel
                                #     # Sharpening kernel
                                #     sharpen_kernel = np.array([[-1, -1, -1],
                                #                             [-1, 9, -1],
                                #                             [-1, -1, -1]])
                                #     sharpened = cv2.filter2D(scaled_image, -1, sharpen_kernel)

                                #     # STEP 3: Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
                                #     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                                #     enhanced = clahe.apply(sharpened)
                                #     cv2.imwrite('word.jpg', enhanced)
                                #     # Run EasyOCR on the cropped image
                                #     text_result = reader.readtext(enhanced)

                                #     # Extract and print recognized text
                                #     if text_result:
                                #         for (bbox, text, confidence) in text_result:
                                #             print(f"Captured text: {text} (Confidence: {confidence:.2f})")
                                #             # if confidence > 0.2:
                                #                 # wordPath = self.txtIntoAudio(text)
                                #                 # trimmed_path = os.path.join(os.path.basename(os.path.dirname(wordPath)), os.path.basename(wordPath))
                                #                 # trimmed_path = trimmed_path.replace("\\", "/")
                                #                 # print(f"Path to word audio: {trimmed_path}")
                                #                 # window.evaluate_js(f"setPopUpWordConfidence('{trimmed_path}')")
                                #                 # # Play a ding! sound
                                #                 # window.evaluate_js(f"playOverAudio('Audio/ding.mp3')")
                                #                 # window.evaluate_js(f"goToScreen('popUpWord')")

                        # Draw hand landmarks on the image
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Display the image
                cv2.imshow('Point to Capture', image)

                if cv2.waitKey(5) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

            self.processing_queue.put((None, None))

        worker_thread = threading.Thread(target=self.process_image_worker, daemon=True)
        worker_thread.start()
            
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
    
    # def process_image(self, base64_image):
    #     window = webview.windows[0]
    #     try:
    #         # Remove the metadata prefix (e.g., "data:image/png;base64,")
    #         image_data = base64_image.split(',')[1]

    #         # Convert base64 string back to binary data
    #         image_binary = base64.b64decode(image_data)

    #         # Save the image to a file (for example, as 'uploaded_image.png')
    #         self.clear_folder('images')
    #         img_folder = "images/"
    #         img_path = img_folder + "analyze.png"
    #         with open(img_path, 'wb') as img_file:
    #             img_file.write(image_binary)

    #         audio_path = self.runModels(img_path)

    #         # Trigger the JS function to play audio after processing the image
    #         # window = webview.windows[0]  # Get the window reference
    #         window.evaluate_js(f'playAudio("{audio_path}");')  # Call the playAudio function in JS

    #         print(img_path)
    #         return {'message': f"Image successfully saved as {img_path}"}
    #     except Exception as e:
    #         print(f"Error processing image: {e}")
    #         window.evaluate_js('displayError();')
    #         return {'message': f"Error processing image: {str(e)}"}
    
    def runModels(self, img_path, bookFolderName, pageNR):       
        image = cv2.imread(img_path)  # Load the image from the file path
        if image is None:
            print("Error: Could not load image. Check the file path.")
            return
        
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        reader = easyocr.Reader(['en'], gpu=True)
        text_result = reader.readtext(gray_image)
        # text_result = pytesseract.image_to_string(gray_image)
        combined_text = ""  # Initialize an empty string to store the combined text
        if text_result:
            for (bbox, text, confidence) in text_result:
                if confidence > 0.2:  # Only include text with confidence > 0.2
                    combined_text += text + " "  # Add the text followed by a space

        # Print the combined text
        print(f"Combined text: {combined_text.strip()}")

        if(combined_text.strip() == ""):
            print("No text detected")
            self.clear_folder(f"books/{bookFolderName}")
            os.rmdir(f"books/{bookFolderName}")
            window.evaluate_js(f"goToScreen('ErrorNewBook')")
            window.evaluate_js(f"playAudio('Audio/New_Book_3.mp3')")
            return 
        else:
            text2 = combined_text.strip()
            print("text Detected")

            # response = model.generate_content("Explain how AI works")
            response = model.generate_content(
                f"""
                Firstly:
                - You will be given a text with errors in some letters: '{text2}'.
                - Correct all errors and provide the intended text as truthfully as possible.
                - Only reply with the fully corrected text — do not repeat the input or include any additional comments.
                
                Secondly:
                - Take this corrected text and break it into small sentence parts, separating each part with a '|' character.
                - Splits should occur at natural pause points such as periods ('.'), commas (','), or appropriate places in long sentences where a speaker would naturally pause.
                - Use logical splits that maintain normal sentence flow — meaning it should still sound natural if spoken aloud, with a '|' marking where a brief pause would be.
                
                Important:
                - Only reply with the final output, formatted with '|' as described.
                - Do not repeat or duplicate text from the input.
                - Do not include any extra words or explanations — only the corrected and split text is allowed in the output.
                """
            )
            # print(response)
            print(response.text)
            # responseArr = response.text.split('|')
            # responseArr = list(filter(None, response.text.split('|')))
            responseArr = [item for item in response.text.strip().split('|') if item.strip()]
            print(responseArr)
            window.evaluate_js(f"playAudio('Audio/Scanning_1.mp3')")

            if(response == None):
                print("response is none")
                self.clear_folder(f"books/{bookFolderName}")
                os.rmdir(f"books/{bookFolderName}")
                window.evaluate_js(f"goToScreen('ErrorNewBook')")
                window.evaluate_js(f"playAudio('Audio/New_Book_3.mp3')")
                return
            elif(len(response.text)>500):
                print("Corrected message was too long")
                self.clear_folder(f"books/{bookFolderName}")
                os.rmdir(f"books/{bookFolderName}")
                window.evaluate_js(f"goToScreen('ErrorNewBook')")
                window.evaluate_js(f"playAudio('Audio/New_Book_3.mp3')")
                return
            # text2 = textfromImg.lower()

            # print(text2)
            # create folder for page
            def create_page_folder(bookname, nrvariable):
                # Define the path to the book folder
                book_path = os.path.join("books", bookname)
                # Define the path for the page folder
                page_folder_name = f"page{nrvariable}"
                page_path = os.path.join(book_path, page_folder_name)
                
                # Check if the book folder exists and the page folder does not
                if os.path.exists(book_path) and not os.path.exists(page_path):
                    os.makedirs(page_path)  # Create the page folder
                    print(f"Folder '{page_folder_name}' created in '{book_path}'.")
                    return page_folder_name
                else:
                    print(f"Book folder does not exist or page folder '{page_folder_name}' already exists.")
            
            pageFolder = create_page_folder(bookFolderName,pageNR)
            current_folder = os.path.dirname(os.path.abspath(__file__))  # Get the script's folder

            for sentence in responseArr:
                client = Client("yaseenuom/text-script-to-audio", hf_token=huggingface_token)
                result = client.predict(
                        text=sentence,
                        voice="en-US-AvaMultilingualNeural - en-US (Female)",
                        rate=0,
                        pitch=0,
                        api_name="/predict"
                )
                print(result[0])

                audio_file_path = result[0]  # Local file path

                # Ensure a unique file name by appending a number if the file already exists
                base_name = "output_audio"
                ext = ".mp3"
                output_path = os.path.join(current_folder, f"books/{bookFolderName}/{pageFolder}/{base_name}{ext}")
                counter = 1

                while os.path.exists(output_path):
                    output_path = os.path.join(current_folder, f"books/{bookFolderName}/{pageFolder}/{base_name}_{counter}{ext}")
                    counter += 1

                # Copy the file to the desired location
                shutil.move(audio_file_path, output_path)

                print(f"Audio saved to {output_path}")
            
            page_path = os.path.join(current_folder, f"books/{bookFolderName}/{pageFolder}")
            if os.path.exists(page_path):
                return page_path

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
    
    webview.start()