## Video Analysis Project 
The goal of this project is to be able to analyze video streams as they come in and calculate metrics like latency, 
framerate, quality, VMAF, etc. to get a sense of how a video stream is performing. Over time it could be used to compare 
the quality, reliability, and costs of different stream providers. The first step is going to be to determine the latency 
between a live stream and a "control" stream. 

### Progress so far 
There is three major components to this project - the video server, the video client, and some additional scripts. 
The video server generates a barcode video and streams it using a flask server. The video streaming server is configured 
to be run in a docker container, which can most easily be run as a Fargate task. In the src folder there is an [AWS 
Cloudformation Stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html) that can be deployed
easily. Currently will need to create one's own ECR repo however.  
The second portion is the video receiving client. The client code is responsible for locating and receiving the video
stream, as well as decoding the QRCode's the video stream receives and analyzing/ storing the data relevant for measuring 
video performance.  
The third (and least important) part of the project is the "scripts". These are some random scripts that became relevant 
over the course of development, largely related to testing, creating QRCode videos, and automating some stuff like 
parameter generations for the slurm inputs. 