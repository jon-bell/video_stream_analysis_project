import cv2
import pandas as pd
import time
from src.streamgear_test import StreamThread
import json
import sqlite3
from typing import List
from numpy import ndarray
from dataclasses import dataclass
from threading import Thread, active_count
from concurrent.futures import ThreadPoolExecutor

DEFAULT_VIDEO_URL = "http://127.0.0.1:5000/video/stream.m3u8"

"""
What I'm trying to understand:
* In some cases we receive frames but they can't be decoded into a QR code - why not? 
    * Can probably figure this out with a cv2.imshow()-ing when that try/except hitz
* The MS difference starts at ~40 then goes up again - this is probably bc of the cv2.waitkey() time? 
* Maybe worth pushing frame collection to a totally post processing step or threaded?
    * Calculated time for each frame to be processsed at ~6ms

"""

@dataclass
class FrameRecorder:
    """
    This class is for making easy abstraction around recording frames
    """
    frame: ndarray
    frame_received_counter: int
    time: float
    analysis_number: int

    def process_frame(self, db_name: str, table_name: str="stream_data"):
        """
        Decodes frames and puts them into SQL database
        """
        qr_decoder = cv2.QRCodeDetector()
        original_val, pts, st_code = qr_decoder.detectAndDecode(self.frame)
        values = original_val.replace("'", '"')
        try:
            values = json.loads(values)
        except json.decoder.JSONDecodeError:
            return
        frame_number = values['frame_number']
        time_generated = values['time']
        insert_sql = f"INSERT INTO {table_name}(frame_number, frame_number_received," \
                     " time_generated, time_received, analysis_number) VALUES(?,?,?,?,?)"
        values = [frame_number, self.frame_received_counter, time_generated, self.time, self.analysis_number]
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()
        cursor.execute(insert_sql, values)
        connection.commit()
        connection.close()
        # print(f"Succesfully inserted frame_number: {frame_number}")


class RecorderThread(Thread):

    def __init__(self, frame_recorder: FrameRecorder, db_name: str, table_name: str="stream_data"):
        super().__init__()
        self.frame_recorder = frame_recorder
        self.db_name = db_name
        self.table_name = table_name

    def run(self):
        self.frame_recorder.process_frame(self.db_name, self.table_name)

class RecorderThreadExecutor(Thread):
    """
    This is a thread that takes in a number of FrameRecorders and executes them with thread executor
    """
    def __init__(self, frame_recorders: List[FrameRecorder], db_name: str, table_name: str="stream_data"):
        super().__init__()
        self.frame_recorders = frame_recorders
        self.db_name = db_name
        self.table_name = table_name

    def start(self) -> None:
        with ThreadPoolExecutor() as executor:
            for frame_recorder in self.frame_recorders:
                executor.submit(frame_recorder.process_frame, db_name=self.db_name, table_name=self.table_name)


class StreamAnalyzer:
    """
    This class absorbs a netowork stream and analyzes it for metrics like FPS, frame counts, time lag
    """

    COLUMN_NAMES = ["frame_number", "frame_number_recorded", "frame_number_received", "time_generated", "time_received", "random"]

    def __init__(self, stream_url: str=DEFAULT_VIDEO_URL, database_name="stream_data.db", table_name: str="stream_data"):
        self.stream_url = stream_url
        self.video_log: pd.DataFrame = pd.DataFrame(columns=self.COLUMN_NAMES)
        self.frames_buffer: List[FrameRecorder] = []
        self.database_name = database_name
        self.table_name = table_name
        self.analysis_number = None
        self.set_up_sql()


    def set_up_sql(self) -> None:
        """
        Sets up SQLite database to record raw performance numbers
        """
        create_table_sql = "CREATE TABLE IF NOT EXISTS stream_data (frame_number INT, frame_number_received INT, time_generated INT, time_received INT, analysis_number INT)"
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        connection.commit()
        self.set_analysis_number(cursor)
        connection.close()

    def set_analysis_number(self, cursor: sqlite3.Cursor) -> None:
        """
        Sets an incrementing analysis number in the database. The database will store data from many differnt analysis
        periods, so it's important to be able to distinguish them.
        """
        sql = "SELECT max(analysis_number) from stream_data"
        data = cursor.execute(sql).fetchall()[0][0]
        if data is None:
            self.analysis_number = 0
        else:
            self.analysis_number = data + 1
        print(f"Analysis number {self.analysis_number} set")


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
        count_thread = 0
        while True:
            start_loop = time.time()
            ret, frame = video_capture.read()
            if frame is None:
                break
            self.frames_buffer.append(FrameRecorder(frame=frame, time=time.time(),
                                                    frame_received_counter=frames_recorded_counter,
                                                    analysis_number=self.analysis_number))
            frames_recorded_counter += 1
            if limit_frames is not None and frames_recorded_counter > limit_frames:
                print("Ending frames recording")
                break
            recorder_thread = RecorderThread(frame_recorder=self.frames_buffer.pop(), db_name=self.database_name, table_name=self.table_name)
            recorder_thread.start()
            count_thread += 1
            end_loop = time.time()
            loop_time = (end_loop - start_loop)
            wait_time = wait_ms - loop_time
            print(f"# of active threads: {active_count()}")
            print(f"loop time: {loop_time * 1000}")
            cv2.waitKey(int(wait_time))

    def analyze_stream(self) -> pd.DataFrame:
        """
        This function looks at the video log and generates some metrics related to the stream.
        Metrics it generates for now:
        * Average time between frames received i.e. fps
        * Number of frames lost
        * Variation in time between frames received
        * Time difference between streamer and stream receiver
        """
        connection = sqlite3.connect(self.database_name)
        sql_query = f"SELECT * FROM {self.table_name} where analysis_number = {self.analysis_number}"
        data = pd.read_sql(sql_query, connection)
        data.sort_values(by=["frame_number"])
        data['time_difference'] = data['time_received'] - data['time_generated']
        data['difference_between_frame_times'] = data['time_received'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0])
        data['calculated_fps'] = 1000 / (data['difference_between_frame_times'] * 1000)
        return data

    def run_and_analyze_stream(self, frame_limit: int=2000, outfile: str="data.csv") -> None:
        """
        This function runs the whole pipeline of running the program that generates and streams the qrcode network
        stream video in a separate thread, then starts receiving and recording the data from the frames, and finally
        processes the data recorded after the fact.
        :param frame_limit: Number of frames to give for the stream and stream recorder. i.e. if 2000 is given,
        then it will process 2000 frames before
        """
        self.get_stream_record_frames(limit_frames=frame_limit) # Start recording frames
        analyzed_data = self.analyze_stream() # Post processing
        if outfile is not None:
            analyzed_data.to_csv(outfile)


if __name__ == '__main__':
    streamer = StreamAnalyzer()
    streamer.run_and_analyze_stream(frame_limit=1000)
