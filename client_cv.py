import cv2
import pandas as pd
import time
import json
import sqlite3
from typing import List
from numpy import ndarray
from dataclasses import dataclass
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import boto3
import argparse
import datetime
import requests

def get_public_ip_ecs_task_by_id(task_identifier: str, cluster_name: str="StreamingClusterCluster") -> str:
    """
    Gets the public IP to connect to for an ecs task
    :param stack_name: name of the stack it's all deployed in... May e a better way to do this
    :return: the public ip of the ecs container
    """
    ecs_client, ec2_client = boto3.client("ecs"), boto3.client("ec2")
    tasks = ecs_client.list_tasks(cluster=cluster_name)['taskArns']
    if not tasks:
        raise AssertionError(f"No tasks associated with cluster {cluster_name}")
    task_arn = tasks # For now will just use the first one
    task_descriptions = ecs_client.describe_tasks(tasks=task_arn, cluster=cluster_name)['tasks']
    attachments = None
    for task in task_descriptions:
        overrides_env: List[dict] = task['overrides']['containerOverrides'][0]['environment']
        for env_vars in overrides_env:
            if env_vars['name'] == "ID":
                if env_vars['value'] == task_identifier:
                    attachments = task['attachments']
                    break
    if not attachments:
        raise AssertionError(f"No container found with matching ID {task_identifier}")
    eni_id = None
    for attach in attachments:
        attach_type = attach['type']
        if attach_type == "ElasticNetworkInterface":
            details = attach['details']
            for det in details:
                if det['name'] == "networkInterfaceId":
                    eni_id = det['value']
                    break
            break
    if eni_id is None:
        raise AssertionError(f"ENI ID not found for task {task_arn} in cluster {cluster_name}")
    network_interfaces = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])['NetworkInterfaces']
    public_ip = network_interfaces[0]['Association']['PublicIp']
    return public_ip

# DEFAULT_VIDEO_URL = "http://127.0.0.1:5000/video/stream.m3u8"
# DEFAULT_VIDEO_URL = f"http://{get_public_ip_ecs_task()}:5000/video/stream.m3u8"
new_url = "10.110.126.188"
DEFAULT_VIDEO_URL = f"http://{new_url}:5000/video/stream.m3u8"

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

    def process_frame(self, db_name: str, table_name: str="stream_data", no_logging: bool=False):
        """
        Decodes frames and puts them into SQL database
        """
        qr_decoder = cv2.QRCodeDetector()
        try:
            original_val, pts, st_code = qr_decoder.detectAndDecode(self.frame)
        except cv2.error as e:
            print(f"Frame dropped! Frame number {self.frame_received_counter}")
            cv2.imwrite(f"frame/frame_{self.frame_received_counter}.png", self.frame)
            raise e
            return
        if no_logging:
            return
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

    def __init__(self, frame_recorder: FrameRecorder, db_name: str, table_name: str="stream_data", no_logging: bool=False):
        super().__init__()
        self.frame_recorder = frame_recorder
        self.db_name = db_name
        self.table_name = table_name
        self.no_logging = no_logging

    def run(self):
        self.frame_recorder.process_frame(self.db_name, self.table_name, no_logging=self.no_logging)

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

    def __init__(self, ip_address: str=DEFAULT_VIDEO_URL, database_name="stream_data.db",
                 table_name: str="stream_data", port: int=5000, record_params: bool=True):
        self.server_url = f"http://{ip_address}:{port}/"
        self.stream_url = self.server_url + "video/stream.m3u8"
        self.video_log: pd.DataFrame = pd.DataFrame(columns=self.COLUMN_NAMES)
        self.frames_buffer: List[FrameRecorder] = []
        self.database_name = database_name
        self.table_name = table_name
        self.analysis_number: int
        self.create_metric_sql()
        self.set_up_sql()
        if record_params:
            self.insert_params()


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
        data= cursor.execute(sql).fetchall()[0][0]
        if data is None:
            self.analysis_number = 0
        else:
            self.analysis_number = data + 1
        print(f"Analysis number {self.analysis_number} set")


    def get_stream_record_frames(self, limit_frames: int=None, no_logging: bool=False) -> None:
        """
        This function captures the network stream and records the information it receives into the video log
        :param limit_frames: number of frames to record for until breaking
        """
        video_capture = cv2.VideoCapture(self.stream_url)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        print(f"FPS received: {fps}")
        wait_ms = int(1000/fps)
        frames_recorded_counter, frames_received_counter = 0, 0
        count_thread = 0
        while True:
            start_loop = time.time()
            ret, frame = video_capture.read()
            frames_recorded_counter += 1
            if limit_frames is not None and frames_recorded_counter > limit_frames:
                print("Ending frames recording")
                break
            with ThreadPoolExecutor(max_workers=10) as executor:
                frame_recorder = FrameRecorder(frame=frame, time=time.time(),
                                                    frame_received_counter=frames_recorded_counter,
                                                    analysis_number=self.analysis_number)
                executor.submit(frame_recorder.process_frame, db_name=self.database_name, table_name=self.table_name)
            # frame_recorder = FrameRecorder(frame=frame, time=time.time(),frame_received_counter=frames_recorded_counter,
            #                                analysis_number=self.analysis_number)
            # recorder_thread = RecorderThread(frame_recorder=frame_recorder, db_name=self.database_name, table_name=self.table_name, no_logging=no_logging)
            # if frames_received_counter % 2 == 0:
            #     recorder_thread.start()
            count_thread += 1
            end_loop = time.time()
            loop_time = (end_loop - start_loop) * 1000
            wait_time = wait_ms - loop_time
            print("wait ms: ", wait_time)
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

    def run_and_analyze_stream(self, frame_limit: int=2000, outfile: str="data.csv", no_logging=False) -> None:
        """
        This function runs the whole pipeline of running the program that generates and streams the qrcode network
        stream video in a separate thread, then starts receiving and recording the data from the frames, and finally
        processes the data recorded after the fact.
        :param frame_limit: Number of frames to give for the stream and stream recorder. i.e. if 2000 is given,
        then it will process 2000 frames before
        """
        self.get_stream_record_frames(limit_frames=frame_limit, no_logging=no_logging) # Start recording frames
        analyzed_data = self.analyze_stream() # Post processing
        if outfile is not None:
            analyzed_data.to_csv(outfile)


def get_parser() -> argparse.ArgumentParser:
    time_str = "_".join(str(datetime.datetime.now()).split(" "))
    parser = argparse.ArgumentParser()
    parser.add_argument("-id", "--identifier", help="This identifier should be part of the container override environment variables with the key ID")
    parser.add_argument("-l", "--logging", action="store_true", default=True, help="If not true, will not log anything to local SQLite database")
    parser.add_argument("-ip", "--ip-address", help="Provide a manual ip address to connect to")
    parser.add_argument("-c", "--cluster-name", default="StreamingClusterCluster", help="Provide a manual cluster")
    parser.add_argument("-f", "--frame-limit", type=int, default=10000, help="Provide a specification for how many frames it should record, default is 10,000")
    parser.add_argument("-o", "--outfile", default=f"data_{time_str}.csv", help="Provide a name for the file that will be output")
    return parser

def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    if args.identifier:
        public_ecs_address = get_public_ip_ecs_task_by_id(task_identifier=args.identifier, cluster_name=args.cluster_name)
        video_url = public_ecs_address
        record_params = True
    if args.ip_address:
        video_url = args.ip_address
        record_params = False

    stream_analyzer = StreamAnalyzer(ip_address=video_url, record_params=record_params)
    stream_analyzer.run_and_analyze_stream(frame_limit=args.frame_limit, outfile=args.outfile)

if __name__ == '__main__':
    # print(get_public_ip_ecs_task_by_id("StreamingClusterCluster"))
    main()