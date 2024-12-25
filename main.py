from fastapi import FastAPI, HTTPException
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ECS Cluster, Service, and Container Status API")
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')

def get_metric_statistics(namespace, metric_name, dimensions, start_time, end_time, statistics=['Average', 'Maximum']):
    try:
        response = cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time.isoformat(),
            EndTime=end_time.isoformat(),
            Period=300,
            Statistics=statistics
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            logging.warning(f"No data points found for {metric_name} with dimensions {dimensions}")
        return {
            stat: max((dp.get(stat, 0) for dp in datapoints), default=0) for stat in statistics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metric: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "ECS Cluster, Service, and Container Status API is running"}

@app.get("/asg/cpu")
def get_asg_cpu(asg_name: str):
    try:
        # Time range for metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        metrics = get_metric_statistics(
            namespace='AWS/AutoScaling',
            metric_name='CPUUtilization',
            dimensions=[{'Name': 'AutoScalingGroupName', 'Value': asg_name}],
            start_time=start_time,
            end_time=end_time
        )

        return {
            "asg": asg_name,
            "cpu_utilization": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/ecs/service/{cluster_name}/{service_name}")
def get_service_status(cluster_name: str, service_name: str):
    try:
        # Time range for metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        metrics = {
            metric: get_metric_statistics(
                namespace='AWS/ECS',
                metric_name=metric,
                dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                start_time=start_time,
                end_time=end_time
            )
            for metric in ['CPUUtilization', 'MemoryUtilization']
        }

        # Retrieve ECS service details
        service_details = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        service_status = service_details['services'][0] if service_details['services'] else {}

        return {
            "cluster": cluster_name,
            "service": service_name,
            "metrics": metrics,
            "status": {
                "desiredCount": service_status.get("desiredCount"),
                "runningCount": service_status.get("runningCount"),
                "pendingCount": service_status.get("pendingCount"),
                "status": service_status.get("status")
            }
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/ecs/container/{cluster_name}/{task_arn}")
def get_container_status(cluster_name: str, task_arn: str):
    try:
        # Retrieve task details
        task_details = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        containers = task_details['tasks'][0].get('containers', []) if task_details['tasks'] else []

        # Time range for metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        container_metrics = {}
        for container in containers:
            container_name = container['name']
            metrics = {
                metric: get_metric_statistics(
                    namespace='ECS/ContainerInsights',
                    metric_name=metric,
                    dimensions=[
                        {'Name': 'ClusterName', 'Value': cluster_name},
                        {'Name': 'TaskArn', 'Value': task_arn},
                        {'Name': 'ContainerName', 'Value': container_name}
                    ],
                    start_time=start_time,
                    end_time=end_time
                )
                for metric in ['CPUUtilized', 'MemoryUtilized']
            }
            if all(value == 0 for stat in metrics.values() for value in stat.values()):
                logging.warning(f"Metrics for container {container_name} returned all zeros. Check if Container Insights is enabled.")
            container_metrics[container_name] = metrics

        return {
            "cluster": cluster_name,
            "taskArn": task_arn,
            "containers": container_metrics
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
