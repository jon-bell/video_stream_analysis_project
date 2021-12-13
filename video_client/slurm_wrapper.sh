#!/bin/bash
source /experiment/jon/streaming-benchmark/credentials

set -x
hostname
CONFIGS_FILE=/experiment/jon/streaming-benchmark/video_stream_analysis_project/video_client/slurm_inputs.txt
export PYTHONUNBUFFERED=true

IDX=$1
EXP=$2
sleepTime=$(expr 20 \* $(expr $IDX % 10))

echo "Sleeping for $sleepTime"
sleep $sleepTime

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
pip install wheel
pip install -r ../src/requirements.txt

pip install pandas boto3 requests
rm stream_data.db

python3 start_task_and_client.py --image-size $IMAGE_SIZE --fps $FPS --cpu $CPU --memory $MEMORY --identifier $IDENTIFIER 
#python3 -u start_task_and_client.py --identifier $IDENTIFIER 

cp stream_data.db $LOG_DIR
mv /scratch/log.txt $LOG_DIR/log.txt
