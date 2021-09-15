## Video Analysis Project 
The goal of this project is to be able to analyze video streams as they come in and calculate metrics like latency, 
framerate, quality, VMAF, etc. to get a sense of how a video stream is performing. Over time it could be used to compare 
the quality, reliability, and costs of different stream providers. The first step is going to be to determine the latency 
between a live stream and a "control" stream. 

### Progress so far 
So far there is a python script that generates a QR code video that contains a timestamp as well as some other metadata 
so in theory it could be used as a first example, or overlayed onto another video and that used as an example.

In addition there is a CloudFormation template for setting up an S3 bucket with a CloudFront distribution that can easily
stream the videos.

### Problems so far
Although I'm easily able to stream another .mp4 file I downloaded from this [endpoint](https://d2ouqtwc83zphe.cloudfront.net/earth.mp4)
I get a blank screen when I try and stream a video I generated with the QR codes [here](https://d2ouqtwc83zphe.cloudfront.net/firstVideoMp4).
I'm not sure what the issue is here because the video I generated with QR codes works fine with VLC media player. This
is what I'm looking into now. I'm guessing there is some nuances in openCV and video file formatting that I don't really
understand yet.

## Replicating project set up

Create virtual env for python:  
`python3 -m venv .venv`  
Install reqs:  
`pip3 install -r requirements.txt`  
Generate a sample video:  
`python3 generate_qr_video.py`  
Assuming you are auth'd to an AWS account, create stack for infrastructure. You will want to override the default bucket name with something else:  
`aws cloudformation --template-file bucket_setup.yaml --stack-name <YOUR STACK NAME> --parameter-overrides BucketName=<YOUR BUCKET NAME HERE>`  
Upload file to S3:  
`aws s3 cp <video_file_name> s3://<YOUR BUCKET NAME>/test.mp4`