# How to Install and Run Whisper Dictate

This guide will walk you through setting up the Whisper Dictate app, getting your Hugging Face Token (required for speaker diarization), and running the application.

---

## 1. Get Your Hugging Face Token

The app uses Pyannote for speaker diarization (distinguishing between different speakers). To use this, you need a free Hugging Face access token.

**How to get it:**
1. Go to [Hugging Face](https://huggingface.co/) and create a free account if you don't have one.
2. Visit the [Pyannote Speaker Diarization 3.1 page](https://huggingface.co/pyannote/speaker-diarization-3.1) and accept the user conditions to access the model.
3. Visit the [Pyannote Segmentation 3.0 page](https://huggingface.co/pyannote/segmentation-3.0) and accept the user conditions there as well.
4. Go to your **Settings > Access Tokens** (or click [here](https://huggingface.co/settings/tokens)).
5. Click **New token**, give it a name (like `DictateApp`), select **Read** permissions, and click **Create token**.
6. **Copy** the token (it will start with `hf_...`).

## 2. Set Up the `.env` File

Once you have your token, you need to add it to the app:
1. In the `C:\dictate-app\` folder (or wherever you downloaded the app), create a new file named exactly `.env` (make sure it doesn't have a `.txt` extension).
2. Open it in Notepad.
3. Paste the following line, replacing `YOUR_TOKEN_HERE` with the token you copied:
   ```
   HF_TOKEN=YOUR_TOKEN_HERE
   ```
4. Save and close the file.

## 3. Install the App

The app comes with an automated installer that sets up Python and all required dependencies.

1. Right-click the `install.bat` file and select **Run as Administrator**.
2. The script will check if Python 3.12 is installed. If not, it will download and install it automatically.
   *(Note: If Python is freshly installed, the script will ask you to close the window and run `install.bat` again).*
3. It will install all necessary packages (like `faster-whisper`, `pyannote.audio`, etc.).
4. Wait for the `Installation Complete!` message.

## 4. Run the App

1. Double-click the `run.bat` file to start the application.
2. The app will launch and sit in your system tray (near the clock in the bottom right corner).
   - A **Green** icon means it's ready.
3. Simply hold the **backtick** key ( `` ` `` ) anywhere in Windows to record your voice. Release the key to automatically type out what you said.

> **First Run Note:** The first time you use the app, it will download the Whisper and Pyannote models automatically. This can take a few minutes depending on your internet connection.

## 5. Uninstall (Optional)

If you ever want to remove the app, simply right-click `uninstall.bat` and select **Run as Administrator**. This will cleanly stop the app and remove it.
