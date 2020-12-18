import asyncio
import time
from SpotifyClient import spotify_client
from rpi_ws281x import PixelStrip, Color
import RPi.GPIO as GPIO


class LedTape():
    LED_COUNT = 8        # Number of LED pixels.
    LED_PIN = 18
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False
    LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

    # colorでLEDを光らせてwaitms間スリープ
    def colorWipe(self, strip, color, wait_sec=0):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
            strip.show()
        time.sleep(wait_sec)

    # 初期化
    def __init__(self):
        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
                                self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()

    def cleanup(self):
        self.colorWipe(self.strip, Color(0, 0, 0))


class Motor():
    motor_pins = [26, 19, 22, 27]

    def __init__(self):
        pass


class Spotify():
    def __init__(self):
        self.client = spotify_client.SpotifyClient()  # spotipyクライアントを取得
        self.is_playing = False
        self.track_id = ""
        self.current_music = None

    async def run(self):
        while True:
            result = await self.fetch()
            if (self.track_id != result['item']['id']
                    or self.is_playing != result['is_playing']):
                print("---------- track_changed ----------")
                print("track name:", result["item"]["name"])
                self.set_state(result)

            await asyncio.sleep(3)

    # APIから再生中の曲を取得
    async def fetch(self):
        result = self.client.currently_playing()
        return result

    # 新しい状態をセット
    def set_state(self, new_state):
        self.timestamp = int(new_state["timestamp"])
        self.progress_ms = int(new_state["progress_ms"])
        self.is_playing = new_state["is_playing"]
        self.track_id = new_state["item"]["id"]


class Root():
    def __init__(self):
        self.spotify = Spotify()
        self.ledtape = LedTape()
        self.moter = Motor()

    async def run(self):
        await self.spotify.run()


def main():
    # eventloopの作成
    loop = asyncio.get_event_loop()
    root = Root()

    # 無限ループ
    try:
        loop.run_until_complete(root.run())
    except KeyboardInterrupt:
        print('keybord interrupt')
        root.ledtape.cleanup()
        loop.close()


if __name__ == '__main__':
    main()
