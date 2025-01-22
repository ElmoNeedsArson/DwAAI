# Explanation
This project was built as a university project. The construction was done in nearly one week, and is therefor not very clean code. It uses pywebview to built an android application. The application is hypothetically meant to be used by visually impaired users to scan in books, and listen back to them or read them to their child. It features a mode where interaction with the child when reading is possible. If the child points at words while reading the user will be notified and can decide to engage and hear the specific word. The aim of this application is to improve parent child connection for visually impaired parents and help children in their developmental cycle. To read the paper contact the repository author. 

# Use Instructions

### 1. First create folder in VSCode

### 2. In terminal:
Run:
`git clone https://github.com/username/repository-name.git`

Run:
 `cd pywebview-3.10`

### 3. In VSCode
In folder in vscode create a .venv python environment
1. press: `ctrl+shift+p` -> 
2. python create environment -> 
3. Use python 3.10.0 -> 
4. Install packages in following order:
```bash
py -m pip install easyocr  
py -m pip install pywebview  
py -m pip install gradio_client
py -m pip install mediapipe   
py -m pip install python-dotenv 
py -m pip install pytesseract  
```

###### Check: In test.py if your imports are accepted or underlined. If underlined:
install packages manually

### 4. Test code first time
Terminal command
`python test.py` -> should start application

### 5. Create Images folder
create a folder call it 'images'

### 6. Create .env file
1. create a file called .env
2. paste this:
`HUGGINGFACE_TOKEN="your_huggingface_token"`

Replace a `read` huggingface token in its place and save the file

run it again (`python test.py`)-> should start application

### 7. PyTesseract
install pyTesseract on your computer with this video:
https://www.youtube.com/watch?v=GMMZAddRxs8
Right up untill the 9 minute mark where it works

### 8. Setup Pytesseract
place your path to the tesseract.exe in the .env file
`PYTESSERACT_PATH='Path_to_.exe'`
Most likely: C:/Users/name/AppData/Local/Programs/TesseractOCR/tesseract.exe

### 9. Finished Run code once more
`python test.py`
Test all functions
