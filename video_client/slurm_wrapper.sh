#!/bin/bash
source /experiment/jon/streaming-benchmark/credentials

set -x
hostname
CONFIGS_FILE=/experiment/jon/streaming-benchmark/video_stream_analysis_project/video_client/slurm_inputs.txt

IDX=$1
EXP=$2

JOB_LINE=`sed "${IDX}q;d" $CONFIGS_FILE`
IFS=" " read -r -a array <<< $JOB_LINE
IMAGE_SIZE=${array[0]}
FPS=${array[1]}
CPU=${array[2]}
MEMORY=${array[3]}
IDENTIFIER=${array[4]}


LOG_DIR=/logs/results/streamingBenchmark/$2/$IMAGE_SIZE-$FPS-$CPU-$MEMORY-$IDENTIFIER/
mkdir -p $LOG_DIR

# copy from the NFS to a local spot
cp /experiment/jon/streaming-benchmark/video_stream_analysis_project.tgz /scratch/
cd /scratch
tar xzf video_stream_analysis_project.tgz
cd video_stream_analysis_project/video_client/

python3 -m venv env
source env/bin/activate
pip install pandas boto3 opencv-python-headless opencv-contrib-python-headless requests

python3 start_task_and_client.py --image-size $IMAGE_SIZE --fps $FPS --cpu $CPU --memory $MEMORY --identifier $IDENTIFIER --frame-limit 120

cp stream_data.db $LOG_DIR
mv /scratch/log.txt $LOG_DIR/log.txt