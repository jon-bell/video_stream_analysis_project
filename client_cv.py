import cv2
import pandas as pd
import time
from src.streamgear_test import StreamThread
import json


DEFAULT_VIDEO_URL = "http://127.0.0.1:5000/video/stream.m3u8"

"""
What I'm trying to understand:
* In some cases we receive frames but they can't be decoded into a QR code - why not? 
    * Can probably figure this out with a cv2.imshow()-ing when that try/except hitz
* The MS difference starts at ~40 then goes up again - this is probably bc of the cv2.waitkey() time? 
* Maybe worth pushing frame collection to a totally post processing step or threaded?
    * Calculated time for each frame to be processsed at ~6ms

"""


class StreamAnalyzer:
    """
    This class absorbs a netowork stream and analyzes it for metrics like FPS, frame counts, time lag
    """

    COLUMN_NAMES = ["frame_number", "frame_number_recorded", "frame_number_received", "time_generated", "time_received", "random"]

    def __init__(self, stream_url: str=DEFAULT_VIDEO_URL):
        self.stream_url = stream_url
        self.video_log: pd.DataFrame = pd.DataFrame(columns=self.COLUMN_NAMES)

    def get_stream_record_frames(self, limit_frames: int=None) -> None:
        """
        This function captures the network stream and records the information it receives into the video log
        :param limit_frames: number of frames to record for until breaking
        """
        video_capture = cv2.VideoCapture(self.stream_url)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        print(f"FPS received: {fps}")
        wait_ms = int(1000/fps)
        qr_decoder = cv2.QRCodeDetector()
        frames_recorded_counter, frames_received_counter = 0, 0
        while True:
            start_loop = time.time()
            ret, frame = video_capture.read()
            if frame is None:
                break
            original_val, pts, st_code = qr_decoder.detectAndDecode(frame)
            frames_received_counter += 1
            values = original_val.replace("'", '"')
            try:
                values = json.loads(values)
            except json.decoder.JSONDecodeError:
                # print("Failed to decode frame")
                # cv2.imshow(f"Test_window_{frames_recorded_counter}", frame)
                cv2.waitKey(wait_ms)
                continue
            frame_number = values['frame_number']
            time_generated = values['time']
            time_received = time.time()
            random = values['random']
            new_row = pd.DataFrame(columns=self.COLUMN_NAMES, data=[[frame_number, frames_recorded_counter, frames_received_counter, time_generated, time_received, random]])
            self.video_log: pd.DataFrame = self.video_log.append(new_row)
            frames_recorded_counter += 1
            if limit_frames is not None and frames_recorded_counter > limit_frames:
                print("Ending frames recording")
                break
            print(f"Count frames recorded: {frames_recorded_counter}")
            end_loop = time.time()
            wait_time = wait_ms - (end_loop - start_loop)
            cv2.waitKey(int(wait_time))

    def analyze_stream(self) -> None:
        """
        This function looks at the video log and generates some metrics related to the stream.
        Metrics it generates for now:
        * Average time between frames received i.e. fps
        * Number of frames lost
        * Variation in time between frames received
        * Time difference between streamer and stream receiver
        """
        self.video_log['time_difference'] = self.video_log['time_received'] - self.video_log['time_generated']
        self.video_log['difference_between_frame_times'] = self.video_log['time_received'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0])
        self.video_log['calculated_fps'] = 1000 / (self.video_log['difference_between_frame_times'] * 1000)

    def run_and_analyze_stream(self, frame_limit: int=2000) -> None:
        """
        This function runs the whole pipeline of running the program that generates and streams the qrcode network
        stream video in a separate thread, then starts receiving and recording the data from the frames, and finally
        processes the data recorded after the fact.
        :param frame_limit: Number of frames to give for the stream and stream recorder. i.e. if 2000 is given,
        then it will process 2000 frames before
        """
        stream = StreamThread(frame_limit=frame_limit)
        stream.start() # Start streaming
        time.sleep(1)
        self.get_stream_record_frames(limit_frames=frame_limit) # Start recording frames
        self.analyze_stream() # Post processing


if __name__ == '__main__':
    streamer = StreamAnalyzer()
    streamer.get_stream_record_frames(500)
    streamer.analyze_stream()
    streamer.video_log.to_csv("two_proccesses.csv")