from SteppingMotor import stepping_motor
from SpotifyClient import spotify_client
import RPi.GPIO as GPIO
import random
import threading
import time
from rpi_ws281x import PixelStrip, Color


class LedTape(threading.Thread):
    LED_COUNT = 8        # Number of LED pixels.
    LED_PIN = 18
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False
    LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

    def colorWipe(self, strip, color, wait_ms=50):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
            strip.show()
        time.sleep(wait_ms / 1000.0)

    def __init__(self):
        threading.Thread.__init__(self)
        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
                                self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()
        self.is_playing = False
        self.section = None

    def run(self):
        while True:
            if self.is_playing:
                self.colorWipe(self.strip, Color(255, 0, 0))  # Red wipe
                self.colorWipe(self.strip, Color(0, 255, 0))  # Blue wipe
                self.colorWipe(self.strip, Color(0, 0, 255))  # Green wipe
            else:
                self.cleanup()

    def cleanup(self):
        self.colorWipe(self.strip, Color(0, 0, 0))


class FullcolorLED():
    def __init__(self, led_pins):
        pass

    def start(self):
        pass

    def run(self):
        pass


class Spotify(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.client = spotify_client.SpotifyClient()
        self.updated = False
        self.bpm = 120
        self.beats = None
        self.is_playing = False
        self.interval = 3
        self.track_id = ""
        self.timestamp = 0
        self.progress_ms = 0
        self.sections = None

    def run(self):
        while True:
            self.fetch()
            time.sleep(self.interval)

    def set_state(self, new_state):
        self.timestamp = int(new_state["timestamp"])
        self.is_playing = new_state["is_playing"]
        self.track_id = new_state["item"]["id"]
        self.progress_ms = int(new_state["progress_ms"])
        print("******************** state updated ********************")
        self.updated = True

    def fetch(self):
        new_state = self.client.currently_playing()

        if not new_state:
            return

        # トラックの変更を拾う
        if not self.track_id == new_state["item"]["id"]:
            print("---------- track_changed ----------")
            print("track name:", new_state["item"]["name"])
            self.load_beats(new_state["item"]["id"])

        self.set_state(new_state)

    def load_beats(self, track_id):
        print("loading beats ...")
        analysis_object = self.client.track_analysis(track_id)
        self.beats = analysis_object["beats"]
        self.sections = analysis_object["sections"]
        print("completed")


class Motor(threading.Thread):
    def __init__(self, GpioPins):
        threading.Thread.__init__(self)
        self.motor = stepping_motor.SteppingMotor(GpioPins)
        self.reverse = False
        self.step = 1
        self.is_playing = False

    def run(self):
        while True:
            if not self.is_playing:
                continue
            self.motor.rotate_with_step(1, self.reverse)


class Prototype2():
    def __init__(self, spotify, motor, led):
        self.spotify = spotify
        self.motor = motor
        self.led = led
        self.is_playing = False
        self.beats = None
        self.elapsed_time = 0.0
        self.last_beat_index = 0
        self.progress_ms = 0.0
        self.base_time = int(time.time() * 1000)
        self.sections = None
        self.last_section_index = 0

    def _get_latest_beat_index(self, progress_ms):
        sec = progress_ms / 1000
        # print("progress:", sec)
        for i, beat in enumerate(self.beats):
            if sec < float(beat["start"]):
                return i
        return -1

    def get_latest_section_index(self, progress_ms):
        sec = progress_ms / 1000
        for i, section in enumerate(self.sections):
            if sec < float(section["start"]):
                return i
        return -1

    def run(self):
        self.spotify.start()
        self.motor.start()
        self.led.start()
        while True:
            if self.spotify.updated:
                self.is_playing = self.spotify.is_playing
                self.timestamp = self.spotify.timestamp
                self.motor.is_playing = self.is_playing
                self.beats = self.spotify.beats
                self.progress_ms = self.spotify.progress_ms
                self.spotify.updated = False
                self.elapsed_time = 0
                self.base_time = int(time.time() * 1000)
                self.led.is_playing = self.is_playing
                self.sections = self.spotify.sections

            if not self.is_playing:
                continue

            self.elapsed_time = int(time.time() * 1000) - self.base_time
            beat_index = self._get_latest_beat_index(
                self.elapsed_time + self.progress_ms)

            if self.last_beat_index != beat_index:
                self.motor.reverse = not self.motor.reverse
                self.last_beat_index = beat_index

            section_index = self.get_latest_section_index(
                self.elapsed_time + self.progress_ms
            )
            if self.last_section_index != section_index:
                print(self.sections[section_index])
                self.led.section = self.sections[section_index]
                self.last_section_index = section_index

            time.sleep(0.1)


if __name__ == '__main__':
    # led_pins = []
    motor_pins = [26, 19, 22, 27]

    motor = Motor(motor_pins)
    led = LedTape()
    spotify = Spotify()
    prototype2 = Prototype2(spotify, motor, led)
    prototype2.run()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        # ctrl+c でcleanupして終了
        led.cleanup()
        print("interrupted!")
        sys.exit()
