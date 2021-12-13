import boto3
import time
from typing import List

DEFAULT_CLUSTER = "StreamingClusterCluster"

def get_public_ip_ecs_task_by_id(task_identifier: str, cluster_name: str=DEFAULT_CLUSTER) -> str:
    """
    Gets the public IP to connect to for an ecs task
    :param stack_name: name of the stack it's all deployed in... May e a better way to do this
    :return: the public ip of the ecs container
    """
    ecs_client, ec2_client = boto3.client("ecs"), boto3.client("ec2")
    tasks = ecs_client.list_tasks(cluster=cluster_name)['taskArns']
    if not tasks:
        raise AssertionError(f"No tasks associated with cluster {cluster_name}")
    task_arns = tasks # For now will just use the first one
    task_descriptions = ecs_client.describe_tasks(tasks=task_arns, cluster=cluster_name)['tasks']
    attachments = None
    task_arn = None
    for task in task_descriptions:
        overrides_env: List[dict] = task['overrides']['containerOverrides'][0]['environment']
        for env_vars in overrides_env:
            if env_vars['name'] == "ID":
                if env_vars['value'] == task_identifier:
                    attachments = task['attachments']
                    task_arn = task['taskArn']
                    break
    count_loops = 0
    while True:
        last_status = get_last_status(task_arn)
        if last_status == "RUNNING":
            break
        else:
            print(f"Task arn: {task_arn} is currently status {last_status} sleeping for 10 and trying again")
            time.sleep(10)
        count_loops += 1
        if count_loops >= 20:
            raise AssertionError(f"After sleeping for 200 seconds the task {task_arn} is still not running, exiting")
    if not attachments:
        raise AssertionError(f"No container found with matching ID {task_identifier}")
    eni_id = None
    for attach in attachments:
        attach_type = attach['type']
        if attach_type == "ElasticNetworkInterface":
            details = attach['details']
            for det in details:
                if det['name'] == "networkInterfaceId":
                    eni_id = det['value']
                    break
            break
    if eni_id is None:
        raise AssertionError(f"ENI ID not found for task {task_arn} in cluster {cluster_name}")
    network_interfaces = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])['NetworkInterfaces']
    public_ip = network_interfaces[0]['Association']['PublicIp']
    return public_ip


def stop_task_by_id(task_identifier: str, cluster_name: str=DEFAULT_CLUSTER) -> dict:
    ecs_client = boto3.client("ecs")
    task_arn = get_task_arn_by_id(task_identifier=task_identifier, cluster_name=cluster_name)
    return ecs_client.stop_task(cluster=cluster_name, task=task_arn)


def get_task_arn_by_id(task_identifier: str, cluster_name: str) -> str:
    ecs_client = boto3.client("ecs")
    tasks = ecs_client.list_tasks(cluster=cluster_name)['taskArns']
    if not tasks:
        raise AssertionError(f"No tasks associated with cluster {cluster_name}")
    task_arns = tasks # For now will just use the first one
    task_descriptions = ecs_client.describe_tasks(tasks=task_arns, cluster=cluster_name)['tasks']
    for task in task_descriptions:
        overrides_env: List[dict] = task['overrides']['containerOverrides'][0]['environment']
        for env_vars in overrides_env:
            if env_vars['name'] == "ID":
                if env_vars['value'] == task_identifier:
                    return task['taskArn']
    raise AssertionError(f"No task with container with ENV ID = {task_identifier}")


def get_last_status(task_arn: str, cluster: str=DEFAULT_CLUSTER) -> str:
    """
    Gets the "lastStatus" of an ecs task
    :param cluster: Name of the cluster that the task exists in
    :param task_arn: str arn of the task. Can be found with `aws ecs list-tasks --cluster XXX`
    :return: str of the lastStatus of the cluster i.e "PROVISIONING" or "RUNNING"
    """
    client = boto3.client("ecs")
    task = client.describe_tasks(tasks=[task_arn], cluster=cluster)['tasks'][0]
    last_status = task['lastStatus']
    return last_status