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
WIDTH, HEIGHT = 800, 600
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
            {"name": "Spectrum (64 bars)", "function": self.draw_spectrum_v1, "default_sensitivity": 2.0},
            {"name": "Blue Bars (7 bars)", "function": self.draw_spectrum_v2, "default_sensitivity": 4.5},
            {"name": "Old School LED", "function": self.draw_led_spectrum, "default_sensitivity": 4.5},
            {"name": "Kaleidoscope", "function": self.draw_kaleidoscope, "default_sensitivity": 1.0},
            {"name": "Kaleidoscope v2", "function": self.draw_kaleidoscope_v2, "default_sensitivity": 1.0},
            {"name": "Rotating Bars", "function": self.draw_rotating_bars, "default_sensitivity": 1.5},
            {"name": "Waveform", "function": self.draw_waveform, "default_sensitivity": 1.0},
            {"name": "Circular Kaleidoscope", "function": self.draw_circular_kaleidoscope, "default_sensitivity": 1.2}
        ]
        self.current_vis_idx = 0
        
        # Audio sensitivity
        self.sensitivity = self.visualizers[self.current_vis_idx]["default_sensitivity"]
        self.animation_time = 0
        
        # Rotating Bars state
        self.recreate_rot_bar_surface()
        self.rot_bar_hue = 0
        
        # Random offsets for movement
        self.max_diamonds = 100
        self.random_offsets = np.random.rand(self.max_diamonds) * 2 * np.pi
        self.random_speeds = 0.5 + np.random.rand(self.max_diamonds) * 1.5
        self.random_drift = np.random.randn(self.max_diamonds, 2) * 0.05 # Random small drifts
        self.random_rot_speeds = (np.random.rand(self.max_diamonds) - 0.5) * 5.0 # Random rotation speeds
        self.random_rot_offsets = np.random.rand(self.max_diamonds) * 2 * np.pi
        
        # Peak tracking for Blue Bars (v2)
        self.v2_bar_count = 7
        self.v2_peaks = np.zeros(self.v2_bar_count)
        self.v2_prev_heights = np.zeros(self.v2_bar_count)
        self.v2_increasing = np.zeros(self.v2_bar_count, dtype=bool)

        # Old School LED visualizer state
        self.led_bar_count = 7
        
        # Waveform buffer
        self.waveform_data = np.zeros(1024)
        
        # Circular Kaleidoscope distortion state
        self.ck_distortion_strength = 0.0
        self.ck_distortion_angle = 0.0
        self.ck_target_strength = 0.0
        self.ck_target_angle = 0.0
        self.ck_change_time = 0.0
        
        # Audio sensitivity (initialized to first visualizer's default)
        self.sensitivity = self.visualizers[self.current_vis_idx]["default_sensitivity"]
        
        # Fade surface for v2 trail effect
        self.fade_surface = pygame.Surface((self.width, self.height))
        self.fade_surface.set_alpha(30) # Adjust alpha for fade speed
        self.fade_surface.fill((0, 0, 0))
        
        self.find_candidates()
        self.setup_audio()
        self.init_menu()
        
    def recreate_rot_bar_surface(self):
        # Scale with screen: 80% of the minimum dimension
        self.rot_bar_surface_size = int(min(self.width, self.height) * 0.8)
        # Ensure it's at least a reasonable size
        self.rot_bar_surface_size = max(self.rot_bar_surface_size, 100)
        self.rot_bar_surface = pygame.Surface((self.rot_bar_surface_size, self.rot_bar_surface_size), pygame.SRCALPHA)

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
        self.fade_surface.fill((0, 0, 0))
        self.recreate_rot_bar_surface()
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
        
        # SENSITIVITY: Label and Buttons
        current_y += (btn_height + padding) * 2
        self.menu_labels.append(buttons.Text(self.screen, f"SENSITIVITY: {self.sensitivity:.1f}x", start_x / label_size, current_y / label_size, (255, 255, 255), None, label_size))
        
        current_y += btn_height + padding
        half_btn_width = (btn_width - padding) // 2
        self.menu_buttons.append(buttons.Button(self.screen, "-", "sens_down", start_x, current_y, half_btn_width, btn_height))
        self.menu_buttons.append(buttons.Button(self.screen, "+", "sens_up", start_x + half_btn_width + padding, current_y, half_btn_width, btn_height))

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
        new_bars = np.clip(new_bars * self.sensitivity, 0, 1)
        
        # Store waveform data (last 1024 samples)
        # We use a bit of sensitivity here too for visualization
        self.waveform_data = np.clip(audio_data * self.sensitivity, -1, 1)
        
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
                            elif btn.text_return == "sens_up":
                                self.sensitivity = min(5.0, self.sensitivity + 0.1)
                                self.init_menu()
                            elif btn.text_return == "sens_down":
                                self.sensitivity = max(0.1, self.sensitivity - 0.1)
                                self.init_menu()
                    
                    # Check visualizer buttons
                    for btn in self.visualizer_buttons:
                        btn.check_if_over(position)
                        if btn.over:
                            if btn.text_return.startswith("vis_"):
                                idx = int(btn.text_return.split("_")[1])
                                self.current_vis_idx = idx
                                self.sensitivity = self.visualizers[self.current_vis_idx]["default_sensitivity"]
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
                        self.fade_surface.fill((0, 0, 0))
                        self.recreate_rot_bar_surface()
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
                        self.sensitivity = self.visualizers[self.current_vis_idx]["default_sensitivity"]
                        self.init_menu()
                    elif event.key == pygame.K_m:
                        self.state = "MENU" if self.state == "VISUALIZER" else "VISUALIZER"
                    elif event.key == pygame.K_UP:
                        self.sensitivity = min(5.0, self.sensitivity + 0.1)
                        self.init_menu()
                    elif event.key == pygame.K_DOWN:
                        self.sensitivity = max(0.1, self.sensitivity - 0.1)
                        self.init_menu()
            
            if self.state == "MENU":
                self.handle_menu_events(events)
            
            # Use semi-transparent clear for v2 and kaleidoscope to allow fading trails
            if self.state == "VISUALIZER" and self.visualizers[self.current_vis_idx]["function"] in [self.draw_spectrum_v2, self.draw_kaleidoscope, self.draw_kaleidoscope_v2, self.draw_rotating_bars, self.draw_waveform, self.draw_circular_kaleidoscope]:
                # These handle their own clearing with alpha surface
                pass
            else:
                self.screen.fill((0, 0, 0))
            
            if self.state == "VISUALIZER":
                # Draw the selected visualization
                self.visualizers[self.current_vis_idx]["function"]()

                if self.visualizers[self.current_vis_idx]["function"] not in [self.draw_spectrum_v2, self.draw_kaleidoscope, self.draw_kaleidoscope_v2, self.draw_rotating_bars, self.draw_waveform, self.draw_circular_kaleidoscope]:
                    # Draw status text for other visualizers (v2/kaleidoscope draw their own to avoid fading)
                    status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
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
        
        # Status text
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_led_spectrum(self):
        # Apply dark background
        self.screen.fill((0, 0, 0))
        
        LED_BAR_COUNT = self.led_bar_count
        resampled_bars = np.zeros(LED_BAR_COUNT)
        chunk_size = BAR_COUNT // LED_BAR_COUNT
        for i in range(LED_BAR_COUNT):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < LED_BAR_COUNT - 1 else BAR_COUNT
            resampled_bars[i] = np.mean(self.bars[start:end])

        bar_width = self.width // LED_BAR_COUNT
        padding = bar_width // 6
        led_spacing = 4
        num_leds = 15
        led_height = (self.height - 100) // num_leds - led_spacing
        # Limit LED height to max 10
        if led_height > 10:
            led_height = 10
        
        for i, val in enumerate(resampled_bars):
            # Calculate how many LEDs should be lit
            lit_leds = int(val * num_leds * 1.2) # multiplier to make it more responsive
            lit_leds = min(lit_leds, num_leds)
            
            for j in range(num_leds):
                # LED color based on position
                if j < 8: # Bottom 8: Green
                    color_on = (0, 255, 0)
                    color_off = (0, 0, 0)
                elif j < 12: # Next 4: Yellow
                    color_on = (255, 255, 0)
                    color_off = (0, 0, 0)
                else: # Top 3: Red
                    color_on = (255, 0, 0)
                    color_off = (0, 0, 0)
                
                is_lit = j < lit_leds
                color = color_on if is_lit else color_off
                
                # Draw LED segment
                rect_x = i * bar_width + padding
                rect_y = self.height - 50 - (j + 1) * (led_height + led_spacing)
                rect_w = bar_width - 2 * padding
                rect_h = led_height
                
                pygame.draw.rect(self.screen, color, (rect_x, rect_y, rect_w, rect_h))
                
                # Draw "glass" effect on lit LEDs
                if is_lit:
                    pygame.draw.rect(self.screen, (255, 255, 255), (rect_x + 2, rect_y + 2, rect_w - 8, 2), 0)

        # Status text
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_rotating_bars(self):
        # Apply fade effect
        self.screen.blit(self.fade_surface, (0, 0))
        
        # Update color cycling
        self.rot_bar_hue = (self.rot_bar_hue + 0.005) % 1.0
        # Convert hue to RGB
        def hue_to_rgb(h):
            # Simple hue to rgb
            h = h * 6
            c = 255
            x = int(c * (1 - abs(h % 2 - 1)))
            if h < 1: return (c, x, 0)
            if h < 2: return (x, c, 0)
            if h < 3: return (0, c, x)
            if h < 4: return (0, x, c)
            if h < 5: return (x, 0, c)
            return (c, 0, x)
            
        color = hue_to_rgb(self.rot_bar_hue)
        
        # Clear the small surface
        self.rot_bar_surface.fill((0, 0, 0, 0))
        
        # Draw bars onto the small surface
        # We'll use 32 bars for better fit on 300px
        num_bars = 32
        resampled_bars = np.zeros(num_bars)
        chunk_size = BAR_COUNT // num_bars
        for i in range(num_bars):
            start = i * chunk_size
            end = (i + 1) * chunk_size
            resampled_bars[i] = np.mean(self.bars[start:end])
            
        bar_w = self.rot_bar_surface_size // num_bars
        for i, val in enumerate(resampled_bars):
            # Draw mirrored bars from center line of the surface
            bar_h = int(val * (self.rot_bar_surface_size // 2) * 0.9)
            if val > 0.01 and bar_h < 2: bar_h = 2
            
            # Draw upwards and downwards from center
            center_y = self.rot_bar_surface_size // 2
            pygame.draw.rect(self.rot_bar_surface, color, (i * bar_w, center_y - bar_h, bar_w - 1, bar_h))
            pygame.draw.rect(self.rot_bar_surface, color, (i * bar_w, center_y, bar_w - 1, bar_h))

        # Rotate the surface
        rotation_angle = self.animation_time * 12 # 12 degrees per second
        rotated_surf = pygame.transform.rotate(self.rot_bar_surface, rotation_angle)
        
        # Blit to center of screen
        rect = rotated_surf.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(rotated_surf, rect)
        
        # Draw status text
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
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
                    (0, -s/2), (s, 0), (0, s/2), (-s, 0)
                ]
                
                rotated_points = []
                cos_r = np.cos(rot)
                sin_r = np.sin(rot)
                
                for px, py in base_points:
                    # Rotate point around its own center
                    rx = px * cos_r - py * sin_r
                    ry = px * sin_r + py * cos_r
                    # Translate to final position relative to screen center
                    #rotated_points.append((cx + x + rx, cy + y + ry))
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
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_kaleidoscope_v2(self):
        # Apply fade effect
        self.screen.blit(self.fade_surface, (0, 0))
        
        # Center of the screen
        cx, cy = self.width // 2, self.height // 2
        
        # Use more diamonds for a busier look, but smaller
        num_diamonds = 24
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
            
            # Color based on a slowly shifting global hue
            # Global hue shifts through the rainbow over time
            global_hue = (self.animation_time * 0.05) % 1.0
            # Each diamond gets a small offset within a limited range (e.g., 0.1 of the color wheel)
            hue_offset = (i / num_diamonds) * 0.1
            hue = (global_hue + hue_offset) % 1.0
            
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
                    #rotated_points.append((cx + x + rx, cy + y + ry))
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
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_waveform(self):
        # Apply fade effect for a trailing oscilloscope look
        self.screen.blit(self.fade_surface, (0, 0))
        
        points = []
        num_samples = len(self.waveform_data)
        
        # Determine center line
        center_y = self.height // 2
        amplitude = self.height // 3
        
        for i in range(num_samples):
            x = int((i / num_samples) * self.width)
            # Waveform data is in range [-1, 1]
            y = int(center_y + (self.waveform_data[i] * amplitude))
            points.append((x, y))
            
        if len(points) > 1:
            # Color cycling
            hue = (self.animation_time * 0.2) % 1.0
            def hue_to_rgb(h):
                h = h * 6
                c = 255
                x = int(c * (1 - abs(h % 2 - 1)))
                if h < 1: return (c, x, 0)
                if h < 2: return (x, c, 0)
                if h < 3: return (0, c, x)
                if h < 4: return (0, x, c)
                if h < 5: return (x, 0, c)
                return (c, 0, x)
            
            color = hue_to_rgb(hue)
            pygame.draw.lines(self.screen, color, False, points, 2)
            
        # Draw status text
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

    def draw_circular_kaleidoscope(self):
        # Apply fade effect
        self.screen.blit(self.fade_surface, (0, 0))
        
        # Update distortion state
        dt = 1/FPS
        self.ck_change_time -= dt
        if self.ck_change_time <= 0:
            # Change target distortion every 2-5 seconds
            self.ck_target_strength = np.random.uniform(0.0, 0.4) # 0.0 is circle, up to 0.4 oval
            self.ck_target_angle = np.random.uniform(0, np.pi)
            self.ck_change_time = np.random.uniform(2.0, 5.0)
            
        # Smoothly interpolate towards targets
        self.ck_distortion_strength += (self.ck_target_strength - self.ck_distortion_strength) * 0.01
        self.ck_distortion_angle += (self.ck_target_angle - self.ck_distortion_angle) * 0.01
        
        cx, cy = self.width // 2, self.height // 2
        max_dim = min(self.width, self.height) // 2
        
        # Use 12 sectors for circular symmetry
        num_sectors = 12
        num_rings = 8
        
        # Resample audio data into 8 bands
        resampled = np.zeros(num_rings)
        chunk = BAR_COUNT // num_rings
        for i in range(num_rings):
            resampled[i] = np.mean(self.bars[i*chunk : (i+1)*chunk])
            
        for r in range(num_rings):
            # Audio value for this ring
            val = resampled[r]
            
            # Base radius for this ring
            base_radius = (r + 1) * (max_dim / (num_rings + 1))
            
            # Ripple effect: modulate distance with a sine wave moving from middle
            ripple = np.sin(self.animation_time * 3.0 - r * 0.8) * (max_dim * 0.05)
            
            # Audio reactive radius
            radius = base_radius + ripple + (val * max_dim * 0.15)
            
            # Rotation for this ring
            ring_rot = self.animation_time * (0.2 + r * 0.1)
            
            # Color cycling
            hue = (self.animation_time * 0.1 + r / num_rings) % 1.0
            def hue_to_rgb(h, v):
                h = h * 6
                c = int(255 * v)
                x = int(c * (1 - abs(h % 2 - 1)))
                if h < 1: return (c, x, 0)
                if h < 2: return (x, c, 0)
                if h < 3: return (0, c, x)
                if h < 4: return (0, x, c)
                if h < 5: return (x, 0, c)
                return (c, 0, x)
            
            color = hue_to_rgb(hue, 0.5 + 0.5 * val)
            
            # Distortion helper
            def get_distorted_pos(angle, r):
                # Basic circle
                x = r * np.cos(angle)
                y = r * np.sin(angle)
                
                # Apply elliptical distortion
                # Rotate point to distortion frame
                cos_da = np.cos(self.ck_distortion_angle)
                sin_da = np.sin(self.ck_distortion_angle)
                xr = x * cos_da + y * sin_da
                yr = -x * sin_da + y * cos_da
                
                # Scale in distortion frame (one axis grows, other shrinks)
                xr *= (1.0 + self.ck_distortion_strength)
                yr *= (1.0 - self.ck_distortion_strength)
                
                # Rotate back
                xf = xr * cos_da - yr * sin_da
                yf = xr * sin_da + yr * cos_da
                
                return cx + xf, cy + yf

            # Draw dots or small circles in a circular pattern
            for s in range(num_sectors):
                angle = (s / num_sectors) * 2 * np.pi + ring_rot
                px, py = get_distorted_pos(angle, radius)
                
                # Size of the element - scaled with screen and audio
                base_node_size = max_dim * 0.03
                size = int(base_node_size + val * (max_dim * 0.1))
                
                # Alternative: Draw a line connecting to the next sector for a ring look
                next_angle = ((s + 1) / num_sectors) * 2 * np.pi + ring_rot
                nx, ny = get_distorted_pos(next_angle, radius)
                
                pygame.draw.line(self.screen, color, (px, py), (nx, ny), max(1, size // 6))
                pygame.draw.circle(self.screen, color, (int(px), int(py)), size // 2)

        # Draw status text
        status_surface = self.font.render(f"Device: {self.active_device_name} | Sensitivity: {self.sensitivity:.1f}x", True, (200, 200, 200))
        self.screen.blit(status_surface, (10, 10))
        help_surface = self.font.render("Press LEFT/RIGHT: Device | F: Fullscreen | V: Visualizer | M: Menu", True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 30))

if __name__ == "__main__":
    vis = Visualizer()
    vis.run()
