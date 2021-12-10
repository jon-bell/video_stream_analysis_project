import boto3
from datetime import datetime, timezone, timedelta
import time

def stop_all_old_tasks(cluster_name: str="StreamingClusterCluster", time_cutoff_hours: int = 24):
    client = boto3.client("ecs")
    tasks = client.list_tasks(cluster=cluster_name)['taskArns']
    describe_tasks = client.describe_tasks(cluster=cluster_name, tasks=tasks)["tasks"]
    time_cutoff = datetime.now(timezone.utc) - timedelta(hours=time_cutoff_hours)
    for task in describe_tasks:
        created_time: datetime = task['createdAt']
        if created_time < time_cutoff:
            print(f"Because it has been running for 24 hours {task['taskArn']}")
            client.stop_task(cluster=cluster_name, task=task['taskArn'])
        else:
            diff_cutoff = created_time - time_cutoff
            print(f"task {task['taskArn']} will be shutoff in {diff_cutoff} hours")



if __name__ == '__main__':
    while True:
        stop_all_old_tasks()
        print("Sleeping for an hour, will check hours again")
        time.sleep(3600) # 1 hour


