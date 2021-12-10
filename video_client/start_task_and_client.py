import copy
import time
from start_stop_streaming import start_run_streaming_task
from client_cv import StreamAnalyzer, get_public_ip_ecs_task_by_id, DEFAULT_CLUSTER
import argparse

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", type=int, default=512, help="Specify the amount of CPU to give the task")
    parser.add_argument("-v", "--video-type", default="LIVE",
                        help="Specify whether the video should be LIVE or PRECORDED. Note currently prerecorded is not implemented")
    parser.add_argument("-m", "--memory", type=float, default=1.0, help="Specify the amount of memory for the given taks")
    parser.add_argument("-f", "--fps", type=float, default=25.0, help="Give an fps amount i.e. 25.0")
    parser.add_argument("-i", "--image-size", type=int, default=1, help="Give a resolution from 0-3. O-3 stands for 240p, 480p, 720p, and 1080p respectively")
    parser.add_argument("-id", "--identifier", help="Provide a tag for the streaming task so it can be easily identified")
    parser.add_argument("-fl", "--frame-limit", type=int, default=200000, help="Provide a specification for how many frames it should record, default is 10,000")
    parser.add_argument("-cn", "--cluster-name", default=DEFAULT_CLUSTER, help="Provide a manual cluster")
    return parser

def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    streaming_args = copy.copy(args.__dict__)
    del streaming_args['frame_limit']
    del streaming_args['cluster_name']
    streaming = start_run_streaming_task(**streaming_args)
    print("Task started - sleeping for 30 seconds")
    time.sleep(30)
    public_ecs_address = get_public_ip_ecs_task_by_id(task_identifier=args.identifier, cluster_name=args.cluster_name)
    print("Public IP address found, sleeping another 30")
    time.sleep(40)
    stream_analyzer = StreamAnalyzer(ip_address=public_ecs_address, record_params=True)
    stream_analyzer.get_stream_record_frames(args.frame_limit)

if __name__ == '__main__':
    main()