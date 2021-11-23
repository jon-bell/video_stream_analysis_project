import boto3
from typing import List
def get_public_ip_ecs_task_by_id(task_identifier: str, cluster_name: str="StreamingClusterCluster") -> str:
    """
    Gets the public IP to connect to for an ecs task
    :param stack_name: name of the stack it's all deployed in... May e a better way to do this
    :return: the public ip of the ecs container
    """
    ecs_client, ec2_client = boto3.client("ecs"), boto3.client("ec2")
    tasks = ecs_client.list_tasks(cluster=cluster_name)['taskArns']
    if not tasks:
        raise AssertionError(f"No tasks associated with cluster {cluster_name}")
    task_arn = tasks # For now will just use the first one
    task_descriptions = ecs_client.describe_tasks(tasks=task_arn, cluster=cluster_name)['tasks']
    attachments = None
    for task in task_descriptions:
        overrides_env: List[dict] = task['overrides']['containerOverrides'][0]['environment']
        for env_vars in overrides_env:
            if env_vars['name'] == "ID":
                if env_vars['value'] == task_identifier:
                    attachments = task['attachments']
                    break
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

if __name__ == '__main__':
    print(get_public_ip_ecs_task_by_id("test1"))