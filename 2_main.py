from SteppingMotor import stepping_motor
from SpotifyClient import spotify_client
import RPi.GPIO as GPIO
import random
import threading
import time
from rpi_ws281x import PixelStrip, Color
import os

class LedTape(threading.Thread):
    LED_COUNT = 8        # Number of LED pixels.
    LED_PIN = 18
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False
    LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

    def rainbow(self, key, step):
        k = key % 7
        if k == 0:
            return Color(step, 0, 0)
        elif k == 1:
            return Color(0, step, 0)
        elif k == 2:
            return Color(0, 0, step)
        elif k == 3:
            return Color(step, step, 0)
        elif k == 4:
            return Color(step, 0, step)
        elif k == 5:
            return Color(0, step, step)
        elif k == 6:
            return Color(step, step, step)

    def gradation(self, key, step, j):
        k = key % 7
        color_offset =  (j + self.pattern_loop_count) % len(self.rainbow_colors)
        return (self.rainbow_colors[color_offset] + self.rainbow_colors[k]) * step

    # colorでLEDを光らせてwaitms間スリープ
    def colorWipe(self, strip, key, wait_sec=10):
        for i in range(15):
            start = time.time()
            for j in range(strip.numPixels()):
                # strip.setPixelColor(j, self.rainbow(key, i))
                strip.setPixelColor(j, self.gradation(key, i*4, j))
            strip.show()
            elapsed_time = time.time() - start
            sleep_time = (wait_sec / 30) - elapsed_time
            time.sleep(sleep_time if sleep_time >= 0 else 0)
        for i in range(15):
            start = time.time()
            for j in range(strip.numPixels()):
                # strip.setPixelColor(j, self.rainbow(key, 14-i))
                strip.setPixelColor(j, self.gradation(key, (14-i)*4, j))
            strip.show()
            elapsed_time = time.time() - start
            sleep_time = (wait_sec / 30) - elapsed_time
            time.sleep(sleep_time if sleep_time >= 0 else 0)
        self.pattern_loop_count += 1

    # 初期化

    def __init__(self):
        threading.Thread.__init__(self)
        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
                                self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.pattern_loop_count = 0
        self.rainbow_colors = [
            Color(2, 0, 0),
            Color(2, 1, 0),
            Color(2, 2, 0),
            Color(0, 2, 0),
            Color(0, 2, 2),
            Color(0, 0, 2),
            Color(1, 0, 1),
            Color(2, 0, 1)
        ]
        self.strip.begin()
        self.is_playing = False
        self.section = None
        self.beat = None
        self.elapsed_time = 0

    def run(self):
        while True:
            if self.is_playing and self.section:
                key = self.section["key"]
                # 0が入るとダメ
                tempo = self.section["tempo"] if self.section["tempo"] != 0 else 130
                self.colorWipe(self.strip, key, 60/tempo)
            else:
                self.cleanup()

    def cleanup(self):
        self.colorWipe(self.strip, Color(0, 0, 0))


# SpotifyAPIから再生中の曲や、曲の詳細情報を取得する
class Spotify(threading.Thread):
    def __init__(self, cache_path=None):
        threading.Thread.__init__(self)
        self.client = spotify_client.SpotifyClient(cache_path=cache_path)  # spotipyクライアントを用意
        self.updated = False  # 以下取得した情報を保持するフィールド
        self.bpm = 120
        self.beats = None
        self.is_playing = False
        self.interval = 3
        self.track_id = ""
        self.timestamp = 0
        self.progress_ms = 0
        self.sections = None

    # これが無限に回る
    def run(self):
        while True:
            self.fetch()  # fetchして
            time.sleep(self.interval)  # interval

    # フィールドに新しい状態をセットする
    def set_state(self, new_state):
        self.timestamp = int(new_state["timestamp"])
        self.is_playing = new_state["is_playing"]
        self.track_id = new_state["item"]["id"]
        self.progress_ms = int(new_state["progress_ms"])
        if DEBUG: print("******************** state updated ********************")
        self.updated = True

    # fetch関数　APIを叩いて状態を取得
    def fetch(self):
        new_state = self.client.currently_playing()
        if not new_state:  # Spotifyで再生していなかったらreturn
            return

        # 曲の変更を拾う
        if not self.track_id == new_state["item"]["id"]:
            if DEBUG: print("---------- track_changed ----------")
            if DEBUG: print("track name:", new_state["item"]["name"])
            self.load_beats(new_state["item"]["id"])  # 詳細情報を取得する
        self.set_state(new_state)  # 新しい状態をセット

    # analysisを叩いて詳細情報を取得する
    # 曲変更時に呼ばれる
    def load_beats(self, track_id):
        if DEBUG: print("loading beats ...")
        analysis_object = self.client.track_analysis(track_id)
        self.beats = analysis_object["beats"]  # beatと
        self.sections = analysis_object["sections"]  # sectionをセット
        if DEBUG: print("completed")


class Motor(threading.Thread):
    def __init__(self, GpioPins):
        threading.Thread.__init__(self)
        self.motor = stepping_motor.SteppingMotor(GpioPins)
        self.reverse = False
        self.step = 1
        self.is_playing = False
        self.step_count = {
            True: 0,
            False: 0
        }
        self.prev_reverse = False
        self.base_step = 0
        self.reverse_count = 0
        self._reverse = False
        self.lack = False

    def on_track_change(self):
        self.reverse = False
        self.step_count = {
            True: 0,
            False: 0
        }
        self.prev_reverse = False
        self.base_step = 0
        self.reverse_count = 0
        self._reverse = self.reverse

    def run(self):
        while True:
            if not self.is_playing:
                continue
            self._reverse = self.reverse

            # 基準を決まっていない時、基準を決める
            if self.base_step == 0:
                if not self.prev_reverse == self._reverse:
                    self.reverse_count += 1
                    if DEBUG: print(self.reverse_count)
                    if self.reverse_count == 3:
                        self.base_step = int(self.step_count[self.prev_reverse] * 2 / 3)
                        if DEBUG: print("self.base_step:", self.base_step)
                        self.step_count[self.reverse] = 0
            else:
                if not self.prev_reverse == self._reverse:
                    if DEBUG: print(self.step_count)
                    if self.step_count[not self.reverse] == self.step_count[self.reverse]:
                        self.step_count[not self.reverse] = self.base_step
                    self.step_count[self.reverse] = 0

                # 前回のステップ数を超える or 基準を超えていたらスキップ
                if self.step_count[self._reverse] >= self.step_count[not self._reverse] or self.step_count[self._reverse] >= self.base_step:
                    # print("step count over", self.step_count)
                    continue

            # print("reverse:", self.prev_reverse, self._reverse)
            self.step_count[self._reverse] += 1
            self.motor.rotate_with_step(self.step, self._reverse)
            self.prev_reverse = self._reverse

# 各モジュールを管理するクラス
# このクラスを通して情報のやり取りをする


class Prototype2():
    def __init__(self, spotify, motor, led):
        self.spotify = spotify  # spotify
        self.motor = motor  # moter
        self.led = led  # led 各クラスを保持しておく
        self.is_playing = False
        self.beats = None
        self.elapsed_time = 0.0
        self.last_beat_index = 0
        self.progress_ms = 0.0
        self.base_time = int(time.time() * 1000)
        self.sections = None
        self.last_section_index = 0
        self.track_id = ""

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

    # これが呼ばれる 各モジュールを起動する
    def run(self):
        self.spotify.start()
        self.motor.start()
        self.led.start()
        while True:
            if self.spotify.updated:  # 曲が更新されたらspofifyモジュールが持つ情報を親クラスのフィールドに入れる
                self.is_playing = self.spotify.is_playing
                self.timestamp = self.spotify.timestamp
                self.motor.is_playing = self.is_playing
                self.beats = self.spotify.beats
                self.progress_ms = self.spotify.progress_ms
                self.spotify.updated = False
                self.elapsed_time = 0  # 経過時間はゼロになる
                self.base_time = int(time.time() * 1000)
                self.led.is_playing = self.is_playing
                self.sections = self.spotify.sections
                # 音楽の変更を拾う
                if not self.track_id == self.spotify.track_id:
                    self.motor.on_track_change()
                    self.track_id = self.spotify.track_id

            if not self.is_playing:
                continue

            self.elapsed_time = int(time.time() * 1000) - self.base_time

            self.led.elapsed_time = self.elapsed_time

            beat_index = self._get_latest_beat_index(
                self.elapsed_time + self.progress_ms
            )

            if self.last_beat_index != beat_index:
                self.motor.reverse = not self.motor.reverse
                self.last_beat_index = beat_index
                self.led.beat = self.beats[beat_index]

            section_index = self.get_latest_section_index(
                self.elapsed_time + self.progress_ms
            )
            if self.last_section_index != section_index:
                if DEBUG: print(self.sections[section_index])
                self.led.section = self.sections[section_index]
                self.last_section_index = section_index

            time.sleep(0.05)


if __name__ == '__main__':
    DEBUG = True
    # led_pins = []
    motor_pins = [17, 23, 27, 22]

    motor = Motor(motor_pins)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    spotify = Spotify(cache_path=os.path.join(script_dir, "SetupServer/.cache"))
    # spotify = Spotify(cache_path="/home/argon/Project/Prototype/SetupServer/.cache")
    led = LedTape()
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
