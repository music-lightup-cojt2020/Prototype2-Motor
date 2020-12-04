from SteppingMotor import stepping_motor
from RGBLED import fullcolor_led
from SpotifyClient import spotifi_client
import RPi.GPIO as GPIO
import random
import threading
import asyncio

class Prototype1():
  def __init__(self, motor_pins, led_pins, spotify_config):
    super(Prototype1, self).__init__()
    self.motor = stepping_motor.SteppingMotor(motor_pins)
    self.led = fullcolor_led.FullcolerLED(led_pins)
    self.client = spotifi_client.SpotifyClient()

    self.bpm = 120
    self.bpm_count = 0
  def run_led(self, queue):
    while True:
      if is_playing:
        self.led.blink()
        time.sleep(0.05)
        self.led.blink()
        time.sleep(60 / self.bpm / 4)
      else:
        self.switch_red_led(False)
        time.sleep(0.05)
  
  async def get_bpm(self):
    playing = client.get_now_playing_track()
  

  async def run(self):
    bpm = 120
    while True:
      bpm = await self.get_bpm()

    # led_thd = threading.Thread(name='rename worker1', target=self.run_led, args=(self, ))
    # led_thd.start()

if __name__ == '__main__':
  led_pins = [6, 12, 13]
  motor_pins = [17, 18, 27, 22]

  prototype = Prototype1(motor_pins, led_pins, spotify_config)

  loop = asyncio.get_event_loop()
  loop.run_until_complete(prototype.run())

  # led_thd = threading.Thread(name='rename worker1', target=prototype.run_led, args=(prototype.led,))
  # led_thd.start()

  # led = fullcolor_led.FullcolerLED(led_pins, GPIO.BCM)
  # while True:
  #   r = random.randint(0, 100)
  #   g = random.randint(0, 100)
  #   b = random.randint(0, 100)
  #   led.to(r, g, b)
  # motor = stepping_motor.SteppingMotor(GpioPins)
  # # 180度回転
  # motor.rotate(180)
  GPIO.cleanup()