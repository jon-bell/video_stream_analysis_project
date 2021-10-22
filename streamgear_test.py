from vidgear.gears import StreamGear
import cv2
import qrcode
import time
import random
import threading

DEFAULT_FRAMERATE = 25.0

def start_stream(framerate: float=DEFAULT_FRAMERATE, output: str="video\\stream.m3u8", stream_frame_limit: int=None) -> None:
    """
    Starts streaming qr code video to network stream
    """
    options_stream = {"-livestream": True, "-input_framerate": framerate}
    streamer = StreamGear(output=output, format="hls", **options_stream)
    counter = 0
    while True:
        qr_code_data = {"frame_number": counter, "time": time.time(), "random": random.random()}
        qr_code = qrcode.make(data=qr_code_data)
        qr_code.save("temp.png")
        frame = cv2.imread("temp.png")
        streamer.stream(frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("Stream manually terminated. Ending now...")
            break
        if stream_frame_limit is not None and counter > stream_frame_limit:
            print(f"Ending stream because {counter} frames have been sent")
            break
        counter += 1
    streamer.terminate()

class StreamThread(threading.Thread):

    def __init__(self, frame_limit: int = 10000, frame_rate: float=DEFAULT_FRAMERATE):
        super().__init__()
        self.frame_limit = frame_limit
        self.frame_rate = frame_rate

    def run(self) -> None:
        print("Starting stream")
        start_stream(framerate=self.frame_rate, stream_frame_limit=self.frame_limit)
        print("Stream has ended")

if __name__ == '__main__':
    start_stream()

