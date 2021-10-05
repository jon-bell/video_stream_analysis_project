# import necessary libs
import uvicorn, asyncio, cv2
from av import VideoFrame
from aiortc import VideoStreamTrack
from aiortc.mediastreams import MediaStreamError
from vidgear.gears.asyncio import WebGear_RTC
from vidgear.gears.asyncio.helper import reducer
import qrcode
# initialize WebGear_RTC app without any source
web = WebGear_RTC(logging=True)

# create your own Bare-Minimum Custom Media Server
class Custom_RTCServer(VideoStreamTrack):
    """
    Custom Media Server using OpenCV, an inherit-class
    to aiortc's VideoStreamTrack.
    """

    def __init__(self, source=None):

        # don't forget this line!
        super().__init__()

        # initialize global params
        self.stream = cv2.VideoCapture(source)

    async def recv(self):
        """
        A coroutine function that yields `av.frame.Frame`.
        """
        # don't forget this function!!!

        # get next timestamp
        pts, time_base = await self.next_timestamp()

        # read video frame
        (grabbed, frame) = self.stream.read()

        # if NoneType
        if not grabbed:
            return MediaStreamError

        # reducer frames size if you want more performance otherwise comment this line

        frame = await reducer(frame, percentage=30)  # reduce frame by 30%

        # contruct `av.frame.Frame` from `numpy.nd.array`
        av_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        av_frame.pts = pts
        av_frame.time_base = time_base

        # return `av.frame.Frame`
        return av_frame

    def terminate(self):
        """
        Gracefully terminates VideoGear stream
        """
        # don't forget this function!!!

        # terminate
        if not (self.stream is None):
            self.stream.release()
            self.stream = None


# assign your custom media server to config with adequate source (for e.g. foo.mp4)
web.config["server"] = Custom_RTCServer(source="video_test.mp4")

# run this app on Uvicorn server at address http://localhost:8000/
uvicorn.run(web(), host="0.0.0.0", port=8081)

# close app safely
web.shutdown()

if __name__ == '__main__':
    print("test!")