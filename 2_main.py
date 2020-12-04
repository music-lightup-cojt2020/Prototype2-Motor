from SteppingMotor import stepping_motor
from SpotifyClient import spotify_client
import RPi.GPIO as GPIO
import random
import threading
import time

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

    # トラックの変更を拾う
    if not self.track_id == new_state["item"]["id"]:
      print("---------- track_changed ----------")
      print("track name:", new_state["item"]["name"])
      self.load_beats(new_state["item"]["id"])
      self.set_state(new_state)

    # 停止/再生の状態が変化したときのみ、状態をセットする。
    if new_state == None \
        or self.is_playing == new_state["is_playing"]:
      return

    self.set_state(new_state)
    

  def load_beats(self, track_id):
    print("loading beats ...")
    self.beats = self.client.track_analysis(track_id)["beats"]
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

  def _get_latest_beat_index(self, progress_ms):
    sec = progress_ms / 1000
    # print("progress:", sec)
    for i, beat in enumerate(self.beats):
        if sec < float(beat["start"]):
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

      if not self.is_playing:
          continue

      self.elapsed_time =  int(time.time() * 1000) - self.timestamp
      # print(self.elapsed_time / 1000)
      beat_index = self._get_latest_beat_index(self.elapsed_time + self.progress_ms)
      if self.last_beat_index != beat_index:
          self.motor.reverse = not self.motor.reverse
          self.last_beat_index = beat_index

      time.sleep(0.1)

if __name__ == '__main__':
  led_pins = [6, 12, 13]
  motor_pins = [17, 18, 27, 22]

  motor = Motor(motor_pins)
  led = FullcolorLED(led_pins)
  spotify = Spotify()
  prototype2 = Prototype2(spotify, motor, led)
  prototype2.run()

  try:
      while True:
          pass
  except KeyboardInterrupt:
      # ctrl+c でcleanupして終了
      ledService.cleanup()
      print("interrupted!")
      sys.exit()