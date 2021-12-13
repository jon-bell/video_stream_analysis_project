#!/bin/bash
#SBATCH --job-name=StreamBench
#SBATCH --nodes=1 --ntasks=1
#SBATCH --output=/scratch/log.txt
#SBATCH --partition all
#SBATCH --array=1-60
/experiment/jon/streaming-benchmark/video_stream_analysis_project/video_client/slurm_wrapper.sh $SLURM_ARRAY_TASK_ID 2021-12-13-full-run
