import numpy as np
import soundcard as sc
import pygame
import sys
import threading
import warnings

# Suppress SoundCard data discontinuity warnings
try:
    warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)
except AttributeError:
    # If the warning category doesn't exist yet, we'll ignore it by string if needed
    # but SoundCard 0.4.6+ should have it.
    pass

# Constants
WIDTH, HEIGHT = 800, 400
FPS = 60
FFT_SIZE = 2048
BAR_COUNT = 64
SMOOTHING = 0.8
SAMPLE_RATE = 48000

class Visualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SoundCard Loopback Visualizer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)
        
        self.bars = np.zeros(BAR_COUNT)
        self.active_device_name = "None"
        self.candidates = []
        self.current_candidate_idx = 0
        
        self.recorder = None
        self.stop_event = threading.Event()
        self.audio_thread = None
        
        self.find_candidates()
        self.setup_audio()
        
    def find_candidates(self):
        # SoundCard handles WASAPI loopback by including them in all_microphones
        print("DEBUG: Searching for audio devices...")
        try:
            mics = sc.all_microphones(include_loopback=True)
            self.candidates = mics
            print(f"DEBUG: Found {len(self.candidates)} potential candidate devices.")
            for i, dev in enumerate(self.candidates):
                print(f" - Candidate {i}: {dev.name}")
        except Exception as e:
            print(f"Error finding devices: {e}")
            sys.exit(1)
            
        if not self.candidates:
            print("No audio devices found.")
            sys.exit(1)

    def setup_audio(self):
        # Stop existing thread and recorder
        self.stop_audio()
        
        if not self.candidates:
            return

        device = self.candidates[self.current_candidate_idx]
        self.active_device_name = device.name
        print(f"DEBUG: Attempting Audio Capture on: {device.name}")
        
        self.stop_event.clear()
        self.audio_thread = threading.Thread(target=self.audio_capture_loop, args=(device,), daemon=True)
        self.audio_thread.start()

    def stop_audio(self):
        self.stop_event.set()
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
        self.audio_thread = None

    def audio_capture_loop(self, device):
        try:
            # Using a smaller block size can sometimes reduce discontinuities,
            # but SoundCard's record() is already quite efficient.
            # We'll stick to FFT_SIZE for simplicity, as it's a good balance.
            with device.recorder(samplerate=SAMPLE_RATE, blocksize=FFT_SIZE) as recorder:
                print(f"Successfully started capture on: {device.name}")
                while not self.stop_event.is_set():
                    # Read chunks of data
                    # SoundCard's record() can be blocking.
                    data = recorder.record(numframes=FFT_SIZE)
                    if data is not None and len(data) > 0:
                        self.process_audio(data)
        except Exception as e:
            print(f"Error in audio capture loop: {e}")
            self.active_device_name = f"ERROR: {str(e)[:30]}..."

    def process_audio(self, indata):
        # indata has shape (frames, channels) and is typically float32 in SoundCard
        
        # Use the mean of all channels for mono processing
        if len(indata.shape) > 1:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata
        
        # Ensure we have enough data for FFT
        if len(audio_data) < FFT_SIZE:
            # Pad with zeros if necessary
            pad_size = FFT_SIZE - len(audio_data)
            audio_data = np.pad(audio_data, (0, pad_size), 'constant')
        else:
            # Take the last FFT_SIZE samples
            audio_data = audio_data[-FFT_SIZE:]
            
        # Apply window function to reduce leakage
        windowed_data = audio_data * np.hanning(len(audio_data))
        fft_data = np.abs(np.fft.rfft(windowed_data))
        
        # Number of bins in rfft is (n // 2) + 1
        num_bins = len(fft_data)
        
        # Apply a tilt to the spectrum to balance low and high frequencies
        # High frequencies typically have less energy, so we boost them
        # Low frequencies often have too much, so we attenuate them slightly
        freqs = np.linspace(0, SAMPLE_RATE / 2, num_bins)
        # Weighting: gradual boost from 100Hz upwards (approx 3dB/octave tilt)
        weighting = np.sqrt(freqs / 1000.0 + 0.1) 
        fft_data = fft_data * weighting
        
        # Add a small floor to fft_data to reduce noise floor impact
        fft_data = np.maximum(fft_data - 0.002, 0)
        
        # Group FFT bins into bars using a better scale for music
        new_bars = np.zeros(BAR_COUNT)
        
        # Human hearing is roughly 20Hz to 20kHz
        # With 48000Hz sample rate, FFT covers 0 to 24000Hz
        # Bin frequency = idx * (SAMPLE_RATE / FFT_SIZE)
        # 1 bin is ~23.4Hz
        
        # Ignore very low frequencies (below ~60Hz) to avoid DC offset/hum
        min_idx = 3 
        # Most music content is below 14kHz
        max_idx = int(num_bins * (14000 / (SAMPLE_RATE / 2)))
        
        # Logarithmic indices from min_idx to max_idx
        indices = np.logspace(np.log10(min_idx), np.log10(max_idx), BAR_COUNT + 1).astype(int)
        
        for i in range(BAR_COUNT):
            start_idx = indices[i]
            end_idx = max(indices[i+1], start_idx + 1)
            if start_idx < num_bins:
                subset = fft_data[start_idx:min(end_idx, num_bins)]
                if len(subset) > 0:
                    # Taper the very first few bars (sub-bass) to prevent 100% saturation
                    scale_factor = 1.0
                    if i < 3: scale_factor = 0.5 + (i * 0.15)
                    
                    new_bars[i] = (np.max(subset) * 0.6 + np.mean(subset) * 0.4) * scale_factor
        
        # Dynamic Sensitivity / Auto-Gain
        # We'll track the max value seen recently and adjust sensitivity
        if not hasattr(self, 'max_history'):
            self.max_history = []
            
        current_max = np.max(new_bars)
        if current_max > 0.001:
            self.max_history.append(current_max)
        
        # Keep only the last 60 frames (~1 second of audio) for faster response
        if len(self.max_history) > 60:
            self.max_history.pop(0)
            
        # Target a max value of ~0.5 to keep bars lower and prevent "too high" appearance
        if self.max_history:
            # Use 90th percentile to ignore extreme peaks
            target_peak = np.percentile(self.max_history, 90)
            if target_peak > 0:
                dynamic_gain = 0.5 / target_peak
                # Limit gain to a reasonable range
                dynamic_gain = np.clip(dynamic_gain, 0.5, 1000.0)
                new_bars = new_bars * dynamic_gain
        
        # Apply a gentler non-linear scaling
        new_bars = np.power(np.clip(new_bars, 0, 1), 0.75)
            
        # Clip to ensure it's in range [0, 1]
        new_bars = np.clip(new_bars, 0, 1)
        
        # Smoothing (running on a separate thread)
        self.bars = self.bars * 0.5 + new_bars * 0.5

    def next_device(self):
        if not self.candidates: return
        self.current_candidate_idx = (self.current_candidate_idx + 1) % len(self.candidates)
        self.setup_audio()

    def prev_device(self):
        if not self.candidates: return
        self.current_candidate_idx = (self.current_candidate_idx - 1) % len(self.candidates)
        self.setup_audio()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        self.next_device()
                    elif event.key == pygame.K_LEFT:
                        self.prev_device()
            
            self.screen.fill((10, 10, 10))
            
            # Draw bars
            bar_width = WIDTH // BAR_COUNT
            for i, val in enumerate(self.bars):
                # Color gradient based on frequency
                # Lower frequencies (left): Red/Orange
                # Mid frequencies: Green/Cyan
                # High frequencies (right): Blue/Purple
                hue = i / BAR_COUNT
                if hue < 0.33: # Bass -> Red/Yellow
                    color = (255, int(255 * (hue/0.33)), 0)
                elif hue < 0.66: # Mid -> Green/Cyan
                    color = (int(255 * (1 - (hue-0.33)/0.33)), 255, int(255 * ((hue-0.33)/0.33)))
                else: # High -> Blue/Purple
                    color = (int(255 * ((hue-0.66)/0.34)), int(255 * (1 - (hue-0.66)/0.34)), 255)
                
                bar_height = int(val * HEIGHT * 0.8)
                # Ensure a minimum height of 2 pixels for active-ish bars
                if val > 0.01 and bar_height < 2:
                    bar_height = 2
                    
                pygame.draw.rect(
                    self.screen,
                    color,
                    (i * bar_width, HEIGHT - bar_height - 10, bar_width - 1, bar_height)
                )

            # Draw status text
            status_surface = self.font.render(f"Device: {self.active_device_name}", True, (200, 200, 200))
            self.screen.blit(status_surface, (10, 10))
            
            help_surface = self.font.render("Press LEFT/RIGHT to change device", True, (150, 150, 150))
            self.screen.blit(help_surface, (10, 30))
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
        self.stop_audio()
        pygame.quit()

if __name__ == "__main__":
    vis = Visualizer()
    vis.run()
