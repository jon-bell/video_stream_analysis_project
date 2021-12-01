import boto3
from dataclasses import dataclass
import datetime
from typing import List
import argparse

@dataclass
class StackResource:
    LogicalResourceId: str
    PhysicalResourceId: str
    ResourceType: str
    LastUpdatedTimestamp: datetime.datetime
    ResourceStatus: str
    DriftInformation: dict


@dataclass
class Subnet:
    AvailabilityZone: str
    AvailabilityZoneId:  str
    AvailableIpAddressCount: int
    CidrBlock: str
    DefaultForAz: bool
    MapPublicIpOnLaunch: bool
    MapCustomerOwnedIpOnLaunch: bool
    State: str
    SubnetId: str
    VpcId: str
    OwnerId: str
    AssignIpv6AddressOnCreation: bool
    Ipv6CidrBlockAssociationSet: list
    SubnetArn: str
    EnableDns64: bool = True


def start_run_streaming_task(stack_name: str = "streaming", desired_az = "us-east-1a",
                             cpu: int = 512, memory: float = 1, fps: float = 25.0, image_size: int=0,
                             video_type: str = "LIVE", identifier: str = "test") -> dict:
    """
    Starts the task on the cluster for the task
    :param stack_name: str name of the stack
    """
    network_configuration = get_network_configuration(stack_name=stack_name, desired_az=desired_az)
    client = boto3.client("cloudformation")
    stack_resources = client.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    task_definition_arn = None
    cluster_name = None
    for resource in stack_resources:
        resource = StackResource(**resource)
        if resource.ResourceType == "AWS::ECS::TaskDefinition":
            task_definition_arn = resource.PhysicalResourceId
        if resource.ResourceType == "AWS::ECS::Cluster":
            cluster_name = resource.PhysicalResourceId
    if task_definition_arn is None or cluster_name is None:
        raise AssertionError(f"No task definition or no cluster found for stack {stack_name}")
    ecs_client = boto3.client("ecs")
    env_var_override = create_aws_dict({"CPU": cpu, "MEMORY": memory, "FPS":fps, "VIDEO_TYPE":video_type, "IMAGE_SIZE":image_size, "ID":identifier})
    container_override = {"containerOverrides": [{"name": "StreamingCluster", "environment": env_var_override}]}
    run_task_response = ecs_client.run_task(cluster=cluster_name, taskDefinition=task_definition_arn, launchType="FARGATE",
                        platformVersion="LATEST", networkConfiguration=network_configuration, overrides=container_override)
    return run_task_response

def create_aws_dict(python_dict: dict, tags: bool=False) -> List[dict]:
    """
    :param python_dict: any python dictionary
    :return: dictionary in aws env var format like below:
    {

    }
    """
    result = []
    for key, value in python_dict.items():
        new_key_pair = {}
        if tags:
            new_key_pair['key'] = key
        else:
            new_key_pair['name'] = key
        new_key_pair['value'] = str(value)
        result.append(new_key_pair)
    return result

def get_network_configuration(stack_name: str, desired_az: str = "us-east-1a") -> dict:
    """
    Gets the network configuration for launching the ECS task on fargate
    :param stack_name: stack name that the fargate cluster is deployed with
    :return: dict in the below format:
    network_configuration = {
        'awsvpcConfiguration': {
            'subnets': [
                'subnet-05ad5563',
            ],
            'securityGroups': [
                'sg-0e558e3d16795f1f1',
            ],
            'assignPublicIp': 'ENABLED'
        }
    }
    """
    result_dict =     network_configuration = {
        'awsvpcConfiguration': {
            'subnets': [],
            'securityGroups': [],
            'assignPublicIp': 'ENABLED'
        }
    }
    ec2_client = boto3.client("ec2")
    subnets = ec2_client.describe_subnets()['Subnets']
    subnet_id = None
    for subnet in subnets:
        subnet = Subnet(**subnet)
        if subnet.AvailabilityZone == desired_az:
            subnet_id = subnet.SubnetId
    if subnet_id is None:
        raise AssertionError("Not able to find AZ zone")
    result_dict['awsvpcConfiguration']['subnets'].append(subnet_id)
    result_dict['awsvpcConfiguration']['securityGroups'] = get_security_groups()
    return result_dict


def get_security_groups() -> list:
    client = boto3.client("ec2")
    security_groups = client.describe_security_groups()["SecurityGroups"]
    groups = []
    for group in security_groups:
        name = group['GroupName']
        if "ContainerSecurityGroup" in name or "default" in name:
            group_id = group['GroupId']
            groups.append(group_id)
    return groups

def stop_all_tasks_on_cluster(cluster_name: str) -> None:
    client = boto3.client("ecs")
    tasks = client.list_tasks(cluster=cluster_name)['taskArns']
    for taskArn in tasks:
        client.stop_task(cluster=cluster_name, task=taskArn)

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", type=int, default=512, help="Specify the amount of CPU to give the task")
    parser.add_argument("-m", "--memory", type=float, default=1.0, help="Specify the amount of memory for the given taks")
    parser.add_argument("-f", "--fps", type=float, default=25.0, help="Give an fps amount i.e. 25.0")
    parser.add_argument("-i", "--image-size", type=int, default=1, help="Give a resolution from 0-3. O-3 stands for 240p, 480p, 720p, and 1080p respectively")
    parser.add_argument("-id", "--identifier", help="Provide a tag for the streaming task so it can be easily identified")
    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    streaming = start_run_streaming_task(**args.__dict__)
    print(str(streaming))

if __name__ == '__main__':
    main()