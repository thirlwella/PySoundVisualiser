# PySoundVisualiser
Unashamedly using AI for vide coding. I tried doing this a few years ago without help, completely failed. Got this working in a few hours.

I've now added another visualisation with peak lines, and my buttons.py (yes written by me) to the project, so we can have a menu screen 
to change the settings. Top right has text, but I might remove that later as it is a small distraction. Will be thinking of more
elaborate visualisations next update I think.

A Windows-only audio visualizer written in Python. It captures system audio (loopback) using WASAPI and renders a real-time frequency spectrum using Pygame.
 
![Screenshot 2026-04-18 112103.png](assets/Screenshot%202026-04-18%20112103.png)
![Screenshot 2026-04-19 115143.png](assets/Screenshot%202026-04-19%20115143.png)
![Screenshot 2026-04-19 115239.png](assets/Screenshot%202026-04-19%20115239.png)
## 🚀 Features

- **Multiple Visualizations**: Switch between different visual representations of the audio data.
- **WASAPI Loopback Capture**: Captures audio directly from your output devices (Spotify, YouTube, Games) without needing a microphone.
- **Real-time FFT Analysis**: 64-bar frequency spectrum with logarithmic scaling for a balanced musical representation.
- **Dynamic Auto-Gain**: Automatically adjusts sensitivity to ensure bars remain reactive regardless of system volume.
- **Resizable Window & Fullscreen**: Resize the window to any size or press 'F' to toggle fullscreen mode.
- **Interactive Device Switching**: Cycle through available audio output devices in real-time using arrow keys or the control menu.
- **Scrollable Control Menu**: Press 'M' to access a control screen. If the list of devices or visualizers is long, use the **mouse wheel** to scroll.
- **Smooth Visuals**: 60 FPS rendering with various styles (Classic Spectrum, Blue Bars with peak tracking).
- **Robust Driver Support**: Powered by the `SoundCard` library to handle complex Windows audio configurations.

## 📋 Requirements

- **Operating System**: Windows 10/11 (Uses Windows-specific WASAPI)
- **Python**: 3.8 or higher
- **Dependencies**: 
  - `pygame-ce` (or `pygame`)
  - `numpy`
  - `SoundCard`

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/PySoundVisualiser.git
   cd PySoundVisualiser
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Usage

Run the visualizer using Python:

```bash
python main.py
```

### Controls
- **LEFT Arrow**: Switch to the previous audio device.
- **RIGHT Arrow**: Switch to the next audio device.
- **F Key**: Toggle Fullscreen mode.
- **V Key**: Switch to the next visualization style.
- **M Key**: Open/Close Control Menu.
- **Resize Window**: Drag the edges of the window to change its size.
- **Close Window**: Exit the application.

## 🔍 Troubleshooting

### Bose QC45 / Bluetooth Headphones
The application specifically uses the `SoundCard` library to resolve "Invalid number of channels" errors common with Bose and Realtek drivers on Windows. If your headphones are connected, use the arrow keys to find them in the list displayed at the top-left of the window.

### "Data discontinuity" Warnings
You might occasionally see a warning about "data discontinuity in recording" in the console. This is a common notification from the underlying audio drivers when small timing jitter occurs. The application is configured to ignore these to keep the console clean, as they do not affect the visualization quality.

### No Bars Moving?
- Ensure audio is actually playing on the selected device.
- Try switching devices using the arrow keys until you see the correct output name (e.g., `Loopback: Speakers` or `Loopback: Headphones`).

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).
