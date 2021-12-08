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

## Steps to put this into one's own AWS account
1. Create private ECR repo called `fargate-stream`
2. Clone current repo, and build `dockerfile.opencv`, follow [these instructions](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html)
to build and push to ECR repo
3. In the file `fargate_cluster.yaml` replace the parameters "Image" and "VPCId" with values that match your own accounts.
The "Image" parameter should be the same besides replacing with your own AWS Account ID, the VPCId you will have to find and choose your own.
I found mine by running the command `aws ec2 describe-vpcs`, and chose the first option, since I only have one VPC.
4. Now the stack should be ready to be deployed! Run `aws cloudformation deploy --template-file fargate_cluster.yaml --stack-name streaming`
5. If this works without issue we should be able to launch tasks from the cluster, try `python start_task_and_client --id test1` and see if
you can launch a task and start streaming the video!

## Running tests using this 
1. I assume that you will just use a main dev/ root/ general role to deploy the above cloudformation stack
2. To run the client code you will need to put an IAM role on a server with restricted permissions. I made an IAM user with the following permissions:
* ECS Full access
* IAM full access
* EC2 Full access
* Cloudformation Full access  
Though it is definitely possible to restrict further. From there I grabbed the ID and Secrete ID and set them as env variables
on the target server.  
3. For running the tests, the inputs are stored in a file called `slurm_inputs.txt` and consumed by `slurm_wrapper.sh` which should feed those inputs cleanly into `start_task_and_client.py`