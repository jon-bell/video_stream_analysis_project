# import required libraries
from vidgear.gears import ScreenGear
from vidgear.gears import StreamGear
import cv2
import qrcode
import time
import random

# open any valid video stream(for e.g `foo1.mp4` file)
options = {"top": 40, "left": 0, "width": 300, "height": 300}
stream = ScreenGear(monitor=1, logging=True, **options).start()

# describe a suitable manifest-file location/name
options_stream = {"-livestream": True}
streamer = StreamGear(output="video\\stream.m3u8", format = "hls", **options_stream)

# loop over
counter = 0
while True:

    # read frames from stream
    data = {"frame_number": counter, "time": time.time(), "random": random.random()}
    qr_code = qrcode.make(data=data)
    qr_code.save("temp.png")
    image = cv2.imread("temp.png")
    frame = image #stream.read()

    # check for frame if Nonetype
    if frame is None:
        break

    streamer.stream(frame)

    # Show output window
    cv2.imshow("Output Frame", frame)

    # check for 'q' keyq if pressed
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    counter += 1
# close output window
cv2.destroyAllWindows()

# safely close video stream
stream.stop()

# safely close streamer
streamer.terminate()

if __name__ == '__main__':
    print("test")