import datetime
import os
import cv2
from typing import List
import qrcode
from qrcode.image.pil import PilImage
import numpy

now = datetime.datetime.now()
DEFAULT_VIDEO_NAME = "qr_code_video_" + str(now.minute) + str(now.second) + str(now.microsecond) + ".avi"

def generate_qr_codes_and_video(destination_folder: str, sequences, fps, video_name: str=DEFAULT_VIDEO_NAME) -> None:
    """
    Generates full qr_code video
    :param destination_folder: str folder where the qr_codes will reside
    :param sequences: the number of qr_codes to generate (# of unique frames in a video)
    :param fps: the fps of the video. So the length of the video will be (1/fps) * sequences
    """
    if not os.path.exists(destination_folder):
        os.mkdir("../temp_files")
    destination_folder = "temp_files"
    time_between_frames = 60 / fps * 60
    create_sequenced_qr_codes(sequences, "qr_codes", destination_folder, sleep_between_frames=time_between_frames)
    list_images = [destination_folder + "/" + file for file in os.listdir(destination_folder)]
    generate_video_from_images(list_images, video_name, fps)
    temp_files = os.listdir(destination_folder)
    for file in temp_files:
        file_path = os.path.join(destination_folder, file)
        os.remove(file_path)

def generate_video_from_images(list_of_images: List[str], video_file_name: str, fps: int=1) -> None:
    """
    This function takes a list of images and animates them into a video.
    Got a lot of this info from https://theailearner.com/2018/10/15/creating-video-from-images-using-opencv-python/
    :param list_of_images: list of image files to turn into a movie
    :param video_file_name: the name of the video file to be produced
    :param fps: the fps of the video created
    """
    img_array = []
    for filename in list_of_images:
        image = cv2.imread(filename)
        height, width, layers = image.shape
        size = (width, height)
        img_array.append(image)
    video = cv2.VideoWriter(video_file_name, cv2.VideoWriter_fourcc(*'MP4V'), fps, size)
    for img in img_array:
        video.write(img)
    video.release()

def create_sequenced_qr_codes(sequences: int, file_name_base: str, destination: str, sleep_between_frames: float=0.0) -> None:
    """
    Cretes a sequence of QR codes in a destination folder. Each QR code when scanned will have information about the
    time, the number it is in the sequence, and the time between frames
    :param sequences: number of qr codes to generate
    :param destination: folder destination
    :param file_name_base: name of the file. Will be named destination/file_name_base_{file_name_base}
    :param sleep_between_frames: float number of seconds to increment the timestamp. It doesn't actually sleep when
    creating QR codes
    """
    starting_time = datetime.datetime.now()
    for i in range(sequences):
        time_now = starting_time + datetime.timedelta(seconds=i * sleep_between_frames)
        data = {"time_now": time_now, "image_increment":i, "time_increment_per_frame":sleep_between_frames}
        new_qr_code = qrcode.make(data)
        full_file_name = file_name_base + f"_{i}"
        file_name = destination + f"/{full_file_name}.png"
        new_qr_code.save(file_name)

def create_sequenced_qr_codes_in_memory(sequences: int, sleep_between_frames: float=0.0) -> List[PilImage]:
    """
    Cretes a sequence of QR codes in a destination folder. Each QR code when scanned will have information about the
    time, the number it is in the sequence, and the time between frames
    :param sequences: number of qr codes to generate
    :param destination: folder destination
    :param file_name_base: name of the file. Will be named destination/file_name_base_{file_name_base}
    :param sleep_between_frames: float number of seconds to increment the timestamp. It doesn't actually sleep when
    creating QR codes
    """
    starting_time = datetime.datetime.now()
    qr_codes = []
    for i in range(sequences):
        time_now = starting_time + datetime.timedelta(seconds=i * sleep_between_frames)
        data = {"time_now": time_now, "image_increment":i, "time_increment_per_frame":sleep_between_frames}
        qr_code = qrcode.QRCode(version=1)
        qr_code.add_data(data=data)
        qr_code.make()
        image = qr_code.make_image(fill_color="black", back_color="white")
        test_image = image.get_image()
        test_convert = cv2.cvtColor(numpy.array(test_image), cv2.COLOR_RGB2BGR)
        qr_codes.append()
    return qr_codes

if __name__ == '__main__':
    generate_qr_codes_and_video("temp_files", 10000, 25, "video_test.mp4")
    print("test!")