import boto3
from dataclasses import dataclass
import datetime

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

def get_stack_resources(stack_name: str) -> dict:
    client = boto3.client("cloudformation")
    stack_resources = client.list_stack_resources(StackName=stack_name)['StackResourceSummaries']
    result_dict = {}
    for resource in stack_resources:
        sr = StackResource(**resource)

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
    cloudformation_client = boto3.client("cloudformation")
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

def start_run_streaming_task(stack_name: str = "streaming", desired_az = "us-east-1a") -> None:
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
    ecs_client.run_task(cluster=cluster_name, taskDefinition=task_definition_arn, launchType="FARGATE",
                        platformVersion="LATEST", networkConfiguration=network_configuration)

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





if __name__ == '__main__':
    start_run_streaming_task()
