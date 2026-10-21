
***

# 📚 NILAM Auto-Filler (Image Recognition Automation)

This is a Python-based automation script designed to automatically fill out and submit book records on the NILAM system. It uses **OpenCV** for image recognition and **Windows API** for background mouse/keyboard simulation, allowing it to run smoothly without interrupting your workflow.

## ✨ Features
* **Image Recognition:** Locates specific buttons and input fields using template matching (`OpenCV`).
* **Automated Data Entry:** Generates random, realistic English words for Titles, Authors, and Publishers.
* **Smart Rating:** Automatically clicks the 5th star for the rating section.
* **Long Sentence Generation:** Generates grammatically correct sentences exceeding 30 words for the "Summary" and "Moral Value" sections.
* **Multithreading Loop:** Runs continuously in the background with a built-in 3-minute 10-second cooldown between submissions.
* **High DPI Support:** Handles Windows display scaling correctly to ensure accurate clicking coordinates.

---

## ⚙️ Prerequisites & Installation

Before running the script, ensure you have Python installed and install the required dependencies.

1. **Install Python** (Python 3.8 or higher is recommended).
2. **Install the required libraries.** Open your terminal/command prompt and run:
   ```bash
   pip install opencv-python mss numpy pynput
   ```

---

## 🚀 How to Use

### 1. Prepare the Environment
* Make sure the `app.py` (or your script file) and the `Images` folder are in the **same directory**.
* The `Images` folder must contain all the necessary `.png` template screenshots (e.g., `papan_pemuka.png`, `buku.png`, `tambah_rekod.png`, etc.).

### 2. Set up the Browser
* Open the NILAM web page in your browser.
* **IMPORTANT:** Do not minimize the browser window. The script needs to "see" the screen to find the images. You can place it on a second monitor or keep it visible on your main screen.

### 3. Run the Script
* Open your terminal in the script's directory.
* Run the script:
   ```bash
   python app.py
   ```

### 4. Keyboard Controls
* Press **`F6`** to start the automation loop.
* Press **`F7`** to stop the automation loop immediately (it will finish its current minor action before stopping).

---

## 📦 How to Build an Executable (.exe) [Optional]

If you want to run this script without opening VS Code or a terminal, you can compile it into a standalone `.exe` file.

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build the executable (without the black command prompt window):
   ```bash
   python -m PyInstaller -F -w app.py
   ```
3. Move the generated `app.exe` from the `dist` folder to the main folder (where the `Images` folder is located).
4. Double-click `app.exe` to run. Press `F6` to start.

---

## ⚠️ Important Warnings & Limitations

1. **Screen Visibility:** Because the script relies on screen captures (`mss`), **the target web page must remain visible on the screen** while the script is running. If it is completely covered by a full-screen game or minimized, the script will fail.
2. **Anti-Cheat Software:** **DO NOT** use this script while running games with strict anti-cheat systems (e.g., Valorant, PUBG, Genshin Impact). The keyboard/mouse simulation may be flagged as a macro and result in a **permanent ban**.
3. **Mouse Interference:** If you are actively using your mouse while the script is typing or clicking, your cursor movements might interfere with the automation. It is best to leave the mouse alone once the script starts.

---

## 🛠️ Troubleshooting

* **`[!] Error: Cannot find image: ...`** 
  Ensure the `Images` folder is in the same directory as the script/EXE, and the file names exactly match the ones in the code.
* **The script clicks the wrong place.**
  Open the `Images` folder. Recapture the specific image. Try to capture only the distinct text or button, avoiding too much blank space or background.
* **The EXE flashes and closes immediately.**
  You might have built it with `-w` and an error occurred silently. Rebuild it without `-w` (`python -m PyInstaller -F app.py`) to see the error message in the terminal.

---
