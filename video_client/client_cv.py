import cv2
import pandas as pd
import time
import sqlite3
from typing import List
from concurrent.futures import ThreadPoolExecutor
import argparse
import datetime
import requests
from aws_utils import get_public_ip_ecs_task_by_id, DEFAULT_CLUSTER
from frame_recorder import FrameRecorder, FrameDict

new_url = "10.110.126.188"
DEFAULT_VIDEO_URL = f"http://{new_url}:5000/video/stream.m3u8"

# Global variables
FRAMES_BUFFER = {}
COUNT_FRAMES_DROPPED = 0
ROLLING_LATENCY = []
CALCULATED_FPS = []
FRAMES_COUNTED = 0
PROCESSED_FRAMES = set()


def handler(future):
    data: FrameDict = future.result()
    if data is None:
        return
    frame_number = data.frame_number_received
    FRAMES_BUFFER[frame_number] = data
    if frame_number != 0 and frame_number - 1 in FRAMES_BUFFER:
        calculate_statistics(FRAMES_BUFFER[frame_number - 1], data)
    if frame_number + 1 in FRAMES_BUFFER:
        calculate_statistics(data, FRAMES_BUFFER[frame_number + 1])
    for frame in [frame_number - 1, frame_number, frame_number + 1]:
        delete_if_done(frame)
        delete_trailing_frame_buffers(frame_number)

def delete_trailing_frame_buffers(frame_number: int, trailing_period: int = 20) -> None:
    """
    This attempts to remove old frames from frame buffer, without interfering with anything
    :param trailing_period:
    :return:
    """
    frame_cutoff = frame_number - trailing_period
    if frame_cutoff < 0:
        return
    frame_numbers = list(FRAMES_BUFFER.keys())
    for frame_number in frame_numbers:
        if frame_number <= frame_cutoff:
            del FRAMES_BUFFER[frame_number]




def delete_if_done(frame_number):
    neighbor_left = frame_number - 1 in FRAMES_BUFFER or frame_number == 0
    neighbor_right = frame_number + 1 in FRAMES_BUFFER
    if neighbor_left and neighbor_right and frame_number in FRAMES_BUFFER:
        del FRAMES_BUFFER[frame_number]


def calculate_statistics(frame1: FrameDict, frame2: FrameDict):
    global COUNT_FRAMES_DROPPED
    global ROLLING_LATENCY
    global CALCULATED_FPS
    global FRAMES_COUNTED
    if frame1.frame_number == frame2.frame_number_received:
        print("Identical frame numbers, skipping")
        return
    if frame1.frame_number != frame2.frame_number - 1:
        COUNT_FRAMES_DROPPED += 1
    difference_between_frame_times = frame2.time_received - frame1.time_received
    if difference_between_frame_times != 0:
        calculated_fps = 1 / difference_between_frame_times
        if calculated_fps <= 100:
            CALCULATED_FPS.append(calculated_fps)
    latency = frame1.time_received - frame1.time_generated
    FRAMES_COUNTED += 1
    if not frame1.is_error_frame():
        ROLLING_LATENCY.append(latency)

def print_state(record_period_serconds: int):
    print(f"size frame buffer: {len(FRAMES_BUFFER)}")
    if FRAMES_COUNTED != 0:
        try:
            fps = FRAMES_COUNTED / record_period_serconds
            latency = sum(ROLLING_LATENCY) / len(ROLLING_LATENCY)
            print(f"Total fps: {fps} Total Latency: {latency}")
        except ZeroDivisionError as e:
            return
class StreamAnalyzer:
    """
    This class absorbs a netowork stream and analyzes it for metrics like FPS, frame counts, time lag
    """

    COLUMN_NAMES = ["frame_number", "frame_number_recorded", "frame_number_received", "time_generated", "time_received",
                    "random"]

    def __init__(self, ip_address: str = DEFAULT_VIDEO_URL, database_name="stream_data.db",
                 table_name: str = "stream_data", port: int = 5000, record_params: bool = True, record_period_seconds: int = 10):
        self.server_url = f"http://{ip_address}:{port}/"
        self.stream_url = self.server_url + "video/stream.m3u8"
        self.video_log: pd.DataFrame = pd.DataFrame(columns=self.COLUMN_NAMES)
        self.database_name = database_name
        self.table_name = table_name
        self.analysis_number: int
        self.create_metric_sql()
        self.set_up_sql()
        self.create_final_sql_table()
        self.record_period_seconds = record_period_seconds
        if record_params:
            self.insert_params()

    def create_final_sql_table(self) -> None:
        """
        Sets up sql table meant to store the "final" data on video quality and analysis. The stats will be stored once
        every minute and will calculate stats such as rolling latency, frames dropped over the last minute, calculated
        FPS over that minute, maybe something else?
        """
        create_table_sql = "CREATE TABLE IF NOT EXISTS stream_data_final (minute_count INT," \
                           "frames_received INT, frames_dropped INT, avg_calculated_fps FLOAT, avg_calculated_latency FLOAT, analysis_number INT)"
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        connection.commit()
        connection.close()

    def record_summary_statistics(self, minute_count: int, recording_time_period: int) -> None:
        global ROLLING_LATENCY
        global CALCULATED_FPS
        global COUNT_FRAMES_DROPPED
        global FRAMES_COUNTED
        try:
            fps = FRAMES_COUNTED / recording_time_period
        except ZeroDivisionError as e:
            fps = 0
        try:
            latency = sum(ROLLING_LATENCY) / len(ROLLING_LATENCY)
        except ZeroDivisionError as e:
            latency = 0
        sql = "INSERT INTO stream_data_final (minute_count, frames_dropped, avg_calculated_fps, avg_calculated_latency, analysis_number) VALUES (?,?,?,?,?)"
        values = [minute_count, COUNT_FRAMES_DROPPED, fps, latency, self.analysis_number]
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute(sql, values)
        connection.commit()
        connection.close()
        ROLLING_LATENCY = []
        COUNT_FRAMES_DROPPED = 0
        FRAMES_COUNTED = 0


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

    def insert_params(self) -> None:
        """
        Sets the params in the `stream_params` table
        """
        print(f"SERVER URl:: {self.server_url}")
        params = requests.get(self.server_url + "get_params")
        params_json = params.json()
        print(f"received params: {params}")
        expected_params = ["CPU", "MEMORY", "IMAGE_SIZE", "FPS", "VIDEO_TYPE"]
        values = []
        for param in expected_params:
            values.append(params_json[param])
        values.append(self.analysis_number)
        sql = "INSERT INTO stream_params (cpu, ram, image_size, fps, video_type, analysis_number) VALUES (?,?,?,?,?,?)"
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute(sql, values)
        connection.commit()
        connection.close()

    def create_metric_sql(self) -> None:
        """
        Sets up a sqlite database to record the parameters of the test currently running which are
        * CPU
        * RAM
        * Image size
        * FPS
        * Pre Recorded Video vs. Live Generated
        * Analysis number: Links to stream_data table so that we can compare data accross the different runs
        """
        create_table_sql = "CREATE TABLE IF NOT EXISTS stream_params (cpu INT, ram INT, image_size INT, fps INT, video_type CHAR(255), analysis_number INT)"
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        connection.commit()
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

    def get_stream_record_frames(self, limit_frames: int = None, no_logging: bool = False) -> None:
        """
        This function captures the network stream and records the information it receives into the video log
        :param limit_frames: number of frames to record for until breaking
        """
        video_capture = cv2.VideoCapture(self.stream_url)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        print(f"FPS received: {fps}")
        wait_ms = int(1000 / fps)
        frames_recorded_counter, frames_received_counter = 0, 0
        time_last_data_record = time.time()
        minute_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            while True:
                start_loop = time.time()
                ret, frame = video_capture.read()
                frames_recorded_counter += 1
                if limit_frames is not None and frames_recorded_counter > limit_frames:
                    print("Ending frames recording")
                    break
                frame_recorder = FrameRecorder(frame=frame, time=time.time(),
                                               frame_received_counter=frames_recorded_counter,
                                               analysis_number=self.analysis_number)

                future = executor.submit(frame_recorder.process_frame, db_name=self.database_name,
                                         table_name=self.table_name).add_done_callback(handler)
                record_period_passed = time.time() - time_last_data_record >= self.record_period_seconds
                if record_period_passed:
                    print(f"{self.record_period_seconds} has passed since the last time a frame was recorded, recording now")
                    print(f"Updated calculated FPS: {FRAMES_COUNTED / self.record_period_seconds}")
                    print_state(self.record_period_seconds)
                    self.record_summary_statistics(minute_count, self.record_period_seconds)
                    minute_count += 1
                    time_last_data_record = time.time()

                end_loop = time.time()
                loop_time = (end_loop - start_loop) * 1000
                wait_time = wait_ms - loop_time
                # print("wait ms: ", wait_time)
                if wait_time <= 0:
                    continue
                cv2.waitKey(int(wait_time))

    def analyze_stream(self) -> pd.DataFrame:
        """
        This function looks at the video log and generates some metrics related to the stream.
        Metrics it generates for now:
        * Average time between frames received i.e. fps
        * Number of frames lost
        * Variation in time between frames received
        * Time difference between streamer and stream receiver
        TODO: Disable this when no logging is set
        """
        connection = sqlite3.connect(self.database_name)
        sql_query = f"SELECT * FROM {self.table_name} where analysis_number = {self.analysis_number}"
        data = pd.read_sql(sql_query, connection)
        data = data.sort_values(by=["frame_number"])
        first_frame_received = data['frame_number'].iloc[0]
        data['frame_number_index_to_0'] = data['frame_number'] - first_frame_received
        data['frames_dropped'] = data['frame_number_received'] - data.index
        data['time_difference'] = data['time_received'] - data['time_generated']
        data['difference_between_frame_times'] = data['time_received'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0])
        data['calculated_fps'] = 1000 / (data['difference_between_frame_times'] * 1000)
        return data

    def run_and_analyze_stream(self, frame_limit: int = 2000, outfile: str = "data.csv", no_logging=False) -> None:
        """
        This function runs the whole pipeline of running the program that generates and streams the qrcode network
        stream video in a separate thread, then starts receiving and recording the data from the frames, and finally
        processes the data recorded after the fact.
        :param frame_limit: Number of frames to give for the stream and stream recorder. i.e. if 2000 is given,
        then it will process 2000 frames before
        """
        self.get_stream_record_frames(limit_frames=frame_limit, no_logging=no_logging)  # Start recording frames
        analyzed_data = self.analyze_stream()  # Post processing
        if outfile is not None:
            analyzed_data.to_csv(outfile)

def get_parser() -> argparse.ArgumentParser:
    time_str = "_".join(str(datetime.datetime.now()).split(" "))
    parser = argparse.ArgumentParser()
    parser.add_argument("-id", "--identifier",
                        help="This identifier should be part of the container override environment variables with the key ID")
    parser.add_argument("-l", "--logging", action="store_true", default=True,
                        help="If not true, will not log anything to local SQLite database")
    parser.add_argument("-ip", "--ip-address", help="Provide a manual ip address to connect to")
    parser.add_argument("-c", "--cluster-name", default=DEFAULT_CLUSTER, help="Provide a manual cluster")
    parser.add_argument("-f", "--frame-limit", type=int, default=10000,
                        help="Provide a specification for how many frames it should record, default is 10,000")
    parser.add_argument("-o", "--outfile", default=f"data_{time_str}.csv",
                        help="Provide a name for the file that will be output")
    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    if args.identifier:
        public_ecs_address = get_public_ip_ecs_task_by_id(task_identifier=args.identifier,
                                                          cluster_name=args.cluster_name)
        video_url = public_ecs_address
        record_params = True
    if args.ip_address:
        video_url = args.ip_address
        record_params = False

    stream_analyzer = StreamAnalyzer(ip_address=video_url, record_params=record_params)
    try:
        stream_analyzer.run_and_analyze_stream(frame_limit=args.frame_limit, outfile=args.outfile)
    except ZeroDivisionError:
        print("Received zero division error - sleeping for 15 seconds and trying again because server might still be "
              "starting up")
        time.sleep(15)
        stream_analyzer.run_and_analyze_stream(frame_limit=args.frame_limit, outfile=args.outfile)
    except cv2.error:
        print("Received cv2 error, attempting to connect again after 2s")
        time.sleep(2)
        stream_analyzer.run_and_analyze_stream(frame_limit=args.frame_limit, outfile=args.outfile)



if __name__ == '__main__':
    main()
