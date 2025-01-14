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