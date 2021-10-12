import qrcode
import time
import random
import cv2
from vidgear.gears import ScreenGear
from threading import Thread


class VideoGeneratorWorker(Thread):

    def __init__(self, x_window: int=500, y_window: int=500):
        super().__init__()
        self.x_window = x_window
        self.y_window = y_window

    def run(self) -> None:
        continous_live_video(x_window=self.x_window, y_window=self.y_window)


def capture_live_video(x_window=500, y_window=500, show_screen=True) -> None:
    """
    This function generates a QR code video, records it from the screen, and saves the video to output.mp4
    :param x_window: portion of the screen to generate video on/ record
    :param y_window: portion of screen to generate video on/ record
    :param output_file_name: name of file to be output
    :param show_screen: bool to show screen portion that you're recording, mostly redundant if true
    """
    thread = VideoGeneratorWorker(x_window, y_window)
    thread.start()
    options = {"top": y_window, "left": x_window, "width": 470, "height": 500}
    stream = ScreenGear(monitor=1, logging=True, **options).start()
    while True:
        frame = stream.read()
        if frame is None:
            break
        if show_screen:
            cv2.imshow("Output Frame", frame)
        key = cv2.waitKey(33) & 0xFF
        if key == ord("q"):
            cv2.destroyAllWindows()
            break


def continous_live_video(x_window=500, y_window=500) -> None:
    """
    Continously generates live video frames in a window until the key a is pressed
    """
    counter = 0
    while True:
        data = {"frame_number": counter, "time": time.time(), "random": random.random()}
        qr_code = qrcode.make(data=data)
        qr_code.save("temp.png")
        image = cv2.imread("temp.png")
        cv2.imshow("window", image)
        cv2.moveWindow("window", x_window, y_window)
        counter += 1
        if cv2.waitKey(33) == ord('q'):
            print("Test!")
            break


if __name__ == '__main__':
    capture_live_video()
