import time
from dataclasses import dataclass
from numpy import ndarray
import cv2
import json
import sqlite3

@dataclass
class FrameDict:
    """
    Class meant to make it easy to store the data structure of the frames we store in the FRAMES_BUFFER
    """
    frame_number: int
    frame_number_received: int
    time_generated: time.time
    time_received: time.time
    analysis_number: int

    def is_error_frame(self) -> bool:
        return self.time_generated == -1



@dataclass
class FrameRecorder:
    """
    This class is for making easy abstraction around recording frames
    """
    frame: ndarray
    frame_received_counter: int
    time: float
    analysis_number: int

    def process_frame(self, db_name: str, table_name: str="stream_data", no_logging: bool=False) -> FrameDict:
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
        if no_logging:
            return
        values = original_val.replace("'", '"')
        try:
            values = json.loads(values)
        except json.decoder.JSONDecodeError:
            return FrameDict(**{"frame_number": -1, "frame_number_received": self.frame_received_counter, "time_generated": -1,
                    "time_received": self.time, "analysis_number": self.analysis_number})
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
        values_dict = FrameDict(**{"frame_number": frame_number, "frame_number_received": self.frame_received_counter,
                                   "time_generated": time_generated, "time_received": self.time,
                                   "analysis_number": self.analysis_number})
        return values_dict


