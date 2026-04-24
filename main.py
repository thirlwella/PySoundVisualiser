import numpy as np
import soundcard as sc
import pygame
import pygame.freetype
import sys
import threading
import warnings
import buttons

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
        # Initialize freetype for the buttons library
        pygame.freetype.init()
        self.width, self.height = WIDTH, HEIGHT
        self.fullscreen = False
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
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
        
        # UI State
        self.state = "VISUALIZER" # "VISUALIZER" or "MENU"
        self.menu_buttons = []
        self.device_buttons = []
        self.visualizer_buttons = [] # For switching visualizers in menu
        self.menu_labels = []
        self.menu_scroll_y = 0
        self.menu_total_height = 0
        
        # Visualizers
        self.visualizers = [
            {"name": "Spectrum (64 bars)", "function": self.draw_spectrum_v1},
            {"name": "Blue Bars (7 bars)", "function": self.draw_spectrum_v2},
            {"name": "Kaleidoscope", "function": self.draw_kaleidoscope}
        ]
        self.current_vis_idx = 0
        
        # Animation timer for moving elements
        self.animation_time = 0
        
        # Random offsets for movement
        self.random_offsets = np.random.rand(15) * 2 * np.pi
        self.random_speeds = 0.5 + np.random.rand(15) * 1.5
        self.random_drift = np.random.randn(15, 2) * 0.05 # Random small drifts
        self.random_rot_speeds = (np.random.rand(15) - 0.5) * 5.0 # Random rotation speeds
        self.random_rot_offsets = np.random.rand(15) * 2 * np.pi
        
        # Peak tracking for Blue Bars (v2)
        self.v2_bar_count = 7
        self.v2_peaks = np.zeros(self.v2_bar_count)
        self.v2_prev_heights = np.zeros(self.v2_bar_count)
        self.v2_increasing = np.zeros(self.v2_bar_count, dtype=bool)
        
        # Fade surface for v2 trail effect
        self.fade_surface = pygame.Surface((self.width, self.height))
        self.fade_surface.set_alpha(30) # Adjust alpha for fade speed
        self.fade_surface.fill((10, 10, 10))
        
        self.find_candidates()
        self.setup_audio()
        self.init_menu()
        
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            # Store current size to restore later
            self.width_before_fs, self.height_before_fs = self.width, self.height
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.width_before_fs, self.height_before_fs), pygame.RESIZABLE)
        
        self.width, self.height = self.screen.get_size()
        self.fade_surface = pygame.Surface((self.width, self.height))
        self.fade_surface.set_alpha(30)
        self.fade_surface.fill((10, 10, 10))
        self.init_menu()
        
    def init_menu(self):
        # Clear existing buttons
        self.menu_buttons = []
        self.device_buttons = []
        self.visualizer_buttons = []
        self.menu_labels = []
        
        # Calculate sizes relative to screen size
        btn_width = 300
        btn_height = 30
        padding = 10
        
        start_x = (self.width - btn_width) // 2
        
        # We'll use a virtual Y coordinate and then offset everything by self.menu_scroll_y
        current_y = 50
        
        # Header text
        header_color = (0, 120, 215) # Windows Blue
        label_size = 14
        
        # CONTROL MENU Label
        self.menu_labels.append(buttons.Text(self.screen, "CONTROL MENU", start_x / label_size, current_y / label_size, (255, 255, 255), None, label_size))
        
        # Toggle Fullscreen Button
        fs_text = "Exit Fullscreen (F)" if self.fullscreen else "Go Fullscreen (F)"
        current_y += btn_height + padding
        self.menu_buttons.append(buttons.Button(self.screen, fs_text, "toggle_fs", start_x, current_y, btn_width, btn_height))
        
        # Back to Visualizer Button
        current_y += btn_height + padding
        self.menu_buttons.append(buttons.Button(self.screen, "Back to Visualizer", "back", start_x, current_y, btn_width, btn_height))
        
        # SELECT VISUALIZER: Label
        current_y += (btn_height + padding) * 2
        self.menu_labels.append(buttons.Text(self.screen, "SELECT VISUALIZATION:", start_x / label_size, current_y / label_size, (255, 255, 255), None, label_size))
        
        for i, vis in enumerate(self.visualizers):
            name = vis["name"]
            if i == self.current_vis_idx:
                name = f"> {name} <"
            
            current_y += btn_height + padding
            btn = buttons.Button(self.screen, name, f"vis_{i}", start_x, current_y, btn_width, btn_height)
            self.visualizer_buttons.append(btn)

        # Sound Source Selection
        current_y += (btn_height + padding) * 2
        # SELECT SOUND SOURCE: Label
        self.menu_labels.append(buttons.Text(self.screen, "SELECT SOUND SOURCE:", start_x / label_size, current_y / label_size, (255, 255, 255), None, label_size))
        
        for i, candidate in enumerate(self.candidates):
            # Highlight current device
            name = candidate.name
            if name == self.active_device_name:
                name = f"> {name} <"
            
            current_y += btn_height + padding
            btn = buttons.Button(self.screen, name, f"dev_{i}", start_x, current_y, btn_width, btn_height)
            self.device_buttons.append(btn)
            
        self.menu_total_height = current_y + btn_height + 50 # Add bottom padding
        
        # Ensure scroll is within bounds
        max_scroll = max(0, self.menu_total_height - self.height)
        if self.menu_scroll_y > max_scroll:
            self.menu_scroll_y = max_scroll
        
        # Apply scroll offset
        self.apply_menu_scroll()

    def apply_menu_scroll(self):
        for label in self.menu_labels:
            label.position_y = (label.y * label.size) - self.menu_scroll_y
        
        for btn in self.menu_buttons + self.visualizer_buttons + self.device_buttons:
            # Re-calculate position based on initial relative Y but with current scroll
            # Actually, I'll just store the "base_y" for each button or recalculate them.
            # Since init_menu is called whenever something changes, and it sets the buttons,
            # we can just modify their position_y here.
            # But wait, Button.recalculate uses relative_y.
            # Let's just adjust them directly.
            btn.position_y = (btn.relative_y * btn.font_size) - self.menu_scroll_y
            btn.calc_text_position()

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
        self.init_menu()
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
        # Using a more standard weighting-like curve to balance mids
        # Reduce mids (around 1kHz-4kHz) slightly if they are too dominant
        # Standard weighting: np.sqrt(freqs / 1000.0 + 0.1)
        # Modified: attenuate mids by dividing by a factor that peaks at 2kHz
        mid_attenuation = 1.0 + 0.15 * np.exp(-((np.log10(freqs + 1) - np.log10(2000))**2) / 0.5)
        weighting = np.sqrt(freqs / 1000.0 + 0.1) / mid_attenuation
        fft_data = fft_data * weighting
        
        # Add a small floor to fft_data to reduce noise floor impact
        fft_data = np.maximum(fft_data - 0.001, 0)
        
        # Group FFT bins into bars using a better scale for music
        new_bars = np.zeros(BAR_COUNT)
        
        # Human hearing is roughly 20Hz to 20kHz
        # With 48000Hz sample rate, FFT covers 0 to 24000Hz
        # Bin frequency = idx * (SAMPLE_RATE / FFT_SIZE)
        # 1 bin is ~23.4Hz
        
        # Ignore very low frequencies (below ~60Hz) to avoid DC offset/hum
        min_idx = 3 
        # Most music content is below 16kHz
        max_idx = int(num_bins * (16000 / (SAMPLE_RATE / 2)))
        
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
                    if i < 2: scale_factor = 0.7 + (i * 0.15)
                    
                    new_bars[i] = (np.max(subset) * 0.8 + np.mean(subset) * 0.2) * scale_factor
        
        # Dynamic Sensitivity / Auto-Gain (Per-band and Global)
        # We'll track the max value seen recently for each bar and adjust sensitivity
        if not hasattr(self, 'bar_max_history'):
            self.bar_max_history = [[] for _ in range(BAR_COUNT)]
            
        for i in range(BAR_COUNT):
            if new_bars[i] > 0.0001:
                self.bar_max_history[i].append(new_bars[i])
            if len(self.bar_max_history[i]) > 120: # Keep 2 seconds
                self.bar_max_history[i].pop(0)
                
            if self.bar_max_history[i]:
                # Per-bar normalization: target 0.8 per bar peak
                bar_peak = np.percentile(self.bar_max_history[i], 90)
                if bar_peak > 0:
                    new_bars[i] = new_bars[i] * (0.8 / bar_peak)
        
        # Now apply a global peak target as well to avoid everything being too loud
        current_max = np.max(new_bars)
        if not hasattr(self, 'max_history'):
            self.max_history = []
            
        if current_max > 0.0001:
            self.max_history.append(current_max)
        
        # Keep only the last 60 frames (~1 second of audio)
        if len(self.max_history) > 60:
            self.max_history.pop(0)
            
        # Target a global max value of ~0.9
        if self.max_history:
            target_peak = np.percentile(self.max_history, 95)
            if target_peak > 0.95: # Only compress if it's very loud
                global_gain = 0.9 / target_peak
                new_bars = new_bars * global_gain
        
        # Apply a slight expansive scaling to make it more "punchy"
        new_bars = np.power(np.clip(new_bars, 0, 1), 0.9)
            
        # Clip to ensure it's in range [0, 1]
        new_bars = np.clip(new_bars, 0, 1)
        
        # Smoothing (running on a separate thread)
        self.bars = self.bars * 0.4 + new_bars * 0.6

    def next_device(self):
        if not self.candidates: return
        self.current_candidate_idx = (self.current_candidate_idx + 1) % len(self.candidates)
        self.setup_audio()

    def prev_device(self):
        if not self.candidates: return
        self.current_candidate_idx = (self.current_candidate_idx - 1) % len(self.candidates)
        self.setup_audio()

    def handle_menu_events(self, events):
        position = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                # scroll is in event.y (+ for up, - for down)
                # Multiply by a factor for faster scrolling
                self.menu_scroll_y -= event.y * 30
                max_scroll = max(0, self.menu_total_height - self.height)
                self.menu_scroll_y = np.clip(self.menu_scroll_y, 0, max_scroll)
                self.apply_menu_scroll()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    # Check main menu buttons
                    for btn in self.menu_buttons:
                        btn.check_if_over(position)
                        if btn.over:
                            if btn.text_return == "toggle_fs":
                                self.toggle_fullscreen()
                            elif btn.text_return == "back":
                                self.state = "VISUALIZER"
                    
                    # Check visualizer buttons
                    for btn in self.visualizer_buttons:
                        btn.check_if_over(position)
                        if btn.over:
                            if btn.text_return.startswith("vis_"):
                                idx = int(btn.text_return.split("_")[1])
                                self.current_vis_idx = idx
                                self.init_menu() # Refresh highlights

                    # Check device buttons
                    for btn in self.device_buttons:
                        btn.check_if_over(position)
                        if btn.over:
                            if btn.text_return.startswith("dev_"):
                                idx = int(btn.text_return.split("_")[1])
                                self.current_candidate_idx = idx
                                self.setup_audio()
            
            # Handle mouse hover highlights
            for btn in self.menu_buttons:
                btn.check_if_over(position)
            for btn in self.visualizer_buttons:
                btn.check_if_over(position)
            for btn in self.device_buttons:
                btn.check_if_over(position)

    def run(self):
        running = True
        while running:
            self.animation_time += 1 / FPS
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.width, self.height = event.w, event.h
                        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                        self.fade_surface = pygame.Surface((self.width, self.height))
                        self.fade_surface.set_alpha(30)
                        self.fade_surface.fill((10, 10, 10))
                        self.init_menu()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        self.next_device()
                    elif event.key == pygame.K_LEFT:
                        self.prev_device()
                    elif event.key == pygame.K_f:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_v:
                        self.current_vis_idx = (self.current_vis_idx + 1) % len(self.visualizers)
                        self.init_menu()
                    elif event.key == pygame.K_m:
                        self.state = "MENU" if self.state == "VISUALIZER" else "VISUALIZER"
            
            if self.state == "MENU":
                self.handle_menu_events(events)
            
            # Use semi-transparent clear for v2 and kaleidoscope to allow fading trails
            if self.state == "VISUALIZER" and self.visualizers[self.current_vis_idx]["function"] in [self.draw_spectrum_v2, self.draw_kaleidoscope]:
                # These handle their own clearing with alpha surface
                pass
            else:
                self.screen.fill((10, 10, 10))
            
            if self.state == "VISUALIZER":
                # Draw the selected visualization
                self.visualizers[self.current_vis_idx]["function"]()

                if self.visualizers[self.current_vis_idx]["function"] not in [self.draw_spectrum_v2, self.draw_kaleidoscope]:
                    # Draw status text for other visualizers (v2/kaleidoscope draw their own to avoid fading)
                    status_surface = self.font.render(f"Device: {self.active_device_name}", True, (200, 200, 200))
                    self.screen.blit(status_surface, (10, 10))
                    
                    help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
                    self.screen.blit(help_surface, (10, 30))
            else:
                # Draw Menu
                for label in self.menu_labels:
                    label.text_draw()
                for btn in self.menu_buttons:
                    btn.button_draw()
                for btn in self.visualizer_buttons:
                    btn.button_draw()
                for btn in self.device_buttons:
                    btn.button_draw()
                
                # Draw scrollbar if needed
                if self.menu_total_height > self.height:
                    scrollbar_width = 10
                    scrollbar_x = self.width - scrollbar_width
                    
                    # Track
                    pygame.draw.rect(self.screen, (30, 30, 30), (scrollbar_x, 0, scrollbar_width, self.height))
                    
                    # Handle
                    handle_height = max(20, (self.height / self.menu_total_height) * self.height)
                    handle_y = (self.menu_scroll_y / self.menu_total_height) * self.height
                    pygame.draw.rect(self.screen, (100, 100, 100), (scrollbar_x, handle_y, scrollbar_width, handle_height))
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
        self.stop_audio()
        pygame.quit()

    def draw_spectrum_v1(self):
        # Original 64-bar gradient visualization
        bar_width = self.width // BAR_COUNT
        for i, val in enumerate(self.bars):
            # Color gradient based on frequency
            hue = i / BAR_COUNT
            if hue < 0.33: # Bass -> Red/Yellow
                color = (255, int(255 * (hue/0.33)), 0)
            elif hue < 0.66: # Mid -> Green/Cyan
                color = (int(255 * (1 - (hue-0.33)/0.33)), 255, int(255 * ((hue-0.33)/0.33)))
            else: # High -> Blue/Purple
                color = (int(255 * ((hue-0.66)/0.34)), int(255 * (1 - (hue-0.66)/0.34)), 255)
            
            bar_height = int(val * self.height * 0.8)
            if val > 0.01 and bar_height < 2:
                bar_height = 2
                
            pygame.draw.rect(
                self.screen,
                color,
                (i * bar_width, self.height - bar_height - 10, bar_width - 1, bar_height)
            )

    def draw_spectrum_v2(self):
        # Apply fade effect
        self.screen.blit(self.fade_surface, (0, 0))
        
        # New 7-bar blue-shaded visualization
        V2_BAR_COUNT = self.v2_bar_count
        # Resample our BAR_COUNT (64) bars into 7
        resampled_bars = np.zeros(V2_BAR_COUNT)
        chunk_size = BAR_COUNT // V2_BAR_COUNT
        for i in range(V2_BAR_COUNT):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < V2_BAR_COUNT - 1 else BAR_COUNT
            resampled_bars[i] = np.mean(self.bars[start:end])

        bar_width = self.width // V2_BAR_COUNT
        padding = bar_width // 8
        
        for i, val in enumerate(resampled_bars):
            # Shades of blue: from dark blue to light cyan
            blue_intensity = 150 + int(105 * (i / V2_BAR_COUNT))
            green_intensity = int(200 * (i / V2_BAR_COUNT))
            color = (0, green_intensity, blue_intensity)
            
            bar_height = int(val * self.height * 0.7)
            if val > 0.01 and bar_height < 4:
                bar_height = 4
                
            # Peak logic: detect if we just finished increasing
            if bar_height > self.v2_prev_heights[i]:
                # Still increasing
                self.v2_increasing[i] = True
            elif bar_height < self.v2_prev_heights[i]:
                if self.v2_increasing[i]:
                    # Peak detected! (was increasing, now dropping)
                    self.v2_peaks[i] = self.v2_prev_heights[i]
                    self.v2_increasing[i] = False
            
            self.v2_prev_heights[i] = bar_height
            
            # Draw main bar
            pygame.draw.rect(
                self.screen,
                color,
                (i * bar_width + padding//2, self.height - bar_height - 20, bar_width - padding, bar_height)
            )
            
            # Draw peak line (light grey)
            if self.v2_peaks[i] > 0:
                peak_y = self.height - int(self.v2_peaks[i]) - 20
                pygame.draw.line(
                    self.screen,
                    (200, 200, 200), # Light grey
                    (i * bar_width + padding//2, peak_y),
                    (i * bar_width + padding//2 + bar_width - padding, peak_y),
                    2 # 2 pixels thick
                )
        
        # Draw status text here to avoid them being faded
        status_surface = self.font.render(f"Device: {self.active_device_name}", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_kaleidoscope(self):
        # Apply fade effect
        self.screen.blit(self.fade_surface, (0, 0))
        
        # Center of the screen
        cx, cy = self.width // 2, self.height // 2
        
        # Use more diamonds for a busier look, but smaller
        num_diamonds = 15
        resampled = np.zeros(num_diamonds)
        chunk = BAR_COUNT // num_diamonds
        for i in range(num_diamonds):
            resampled[i] = np.mean(self.bars[i*chunk : (i+1)*chunk])
            
        max_dim = min(self.width, self.height) // 2
        
        for i, val in enumerate(resampled):
            # Distance from center with slight oscillation and random phase
            base_dist = (i + 1) * (max_dim / (num_diamonds + 1))
            # Scale oscillation with screen size
            dist_oscillation = (max_dim * 0.1) * np.sin(self.animation_time * self.random_speeds[i] + self.random_offsets[i])
            dist = base_dist + dist_oscillation
            
            # Size based on audio value: more reactive and slightly larger range
            # Scale base size with screen size (using max_dim as reference)
            size = int(np.power(val, 0.6) * (max_dim * 0.3)) + 2
            
            # Color based on index and time: more vibrant response to audio
            hue = (i / num_diamonds) + (self.animation_time * 0.1) + (self.random_offsets[i] / (2*np.pi))
            # Add audio-reactive brightness to color
            vibrancy = 127 + 128 * val
            color = (
                int(vibrancy * (0.5 + 0.5 * np.sin(hue * 2 * np.pi))),
                int(vibrancy * (0.5 + 0.5 * np.sin(hue * 2 * np.pi + 2*np.pi/3))),
                int(vibrancy * (0.5 + 0.5 * np.sin(hue * 2 * np.pi + 4*np.pi/3)))
            )
            
            # Slowly rotating angle for the base triangle, with per-diamond random speed variation
            rotation_speed = 0.5 * self.random_speeds[i]
            angle = (i / num_diamonds) * (np.pi / 4) + (self.animation_time * rotation_speed) + self.random_offsets[i]
            
            # Base point with a tiny bit of random drift/jitter - scaled with screen size
            bx = dist * np.cos(angle) + self.random_drift[i][0] * (max_dim * 0.05)
            by = dist * np.sin(angle) + self.random_drift[i][1] * (max_dim * 0.05)
            
            # Diamond's own rotation
            diamond_rot = self.animation_time * self.random_rot_speeds[i] + self.random_rot_offsets[i]
            
            def draw_diamond(x, y, s, c, rot):
                # Points of a diamond centered at (0,0) before translation and rotation
                # A diamond is basically a square rotated by 45 degrees, 
                # but here we'll just rotate the 4 cardinal points.
                base_points = [
                    (0, -s), (s, 0), (0, s), (-s, 0)
                ]
                
                rotated_points = []
                cos_r = np.cos(rot)
                sin_r = np.sin(rot)
                
                for px, py in base_points:
                    # Rotate point around its own center
                    rx = px * cos_r - py * sin_r
                    ry = px * sin_r + py * cos_r
                    # Translate to final position relative to screen center
                    rotated_points.append((cx + x + rx, cy + y + ry))
                
                pygame.draw.polygon(self.screen, c, rotated_points)

            # 8-way symmetry
            coords = [
                (bx, by), (by, bx),
                (-bx, by), (-by, bx),
                (bx, -by), (by, -bx),
                (-bx, -by), (-by, -bx)
            ]
            
            for tx, ty in coords:
                draw_diamond(tx, ty, size, color, diamond_rot)

        # Draw status text
        status_surface = self.font.render(f"Device: {self.active_device_name}", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

if __name__ == "__main__":
    vis = Visualizer()
    vis.run()
