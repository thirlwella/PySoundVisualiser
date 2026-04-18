# PySoundVisualiser
Unashamedly using AI for vide coding. This is inital working minimal version of the project. I'll be adding more, not really
even taken the time to look at the code yet tbh. I tried doing this a few years ago without help, completely failed. Got this working in a few hours.
Am amazed and really enjoying myself doing this.

A minimal, high-performance Windows-only audio visualizer written in Python. It captures system audio (loopback) using WASAPI and renders a real-time frequency spectrum using Pygame.
 
![Screenshot 2026-04-18 112103.png](assets/Screenshot%202026-04-18%20112103.png)*(Replace with actual screenshot if available)*

## 🚀 Features

- **WASAPI Loopback Capture**: Captures audio directly from your output devices (Spotify, YouTube, Games) without needing a microphone.
- **Real-time FFT Analysis**: 64-bar frequency spectrum with logarithmic scaling for a balanced musical representation.
- **Dynamic Auto-Gain**: Automatically adjusts sensitivity to ensure bars remain reactive regardless of system volume.
- **Interactive Device Switching**: Cycle through available audio output devices (like Bose QC45, Speakers, etc.) in real-time.
- **Smooth Visuals**: 60 FPS rendering with frequency-based color gradients (Bass: Red/Orange, Mids: Green, Highs: Blue/Purple).
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
