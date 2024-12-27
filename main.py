from fastapi import FastAPI, HTTPException, Query
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Enhanced ECS Cluster and Service Status API")
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')
logs_client = boto3.client('logs')

@app.get("/")
def read_root():
    return {"message": "ECS Cluster and Service Status API is running"}

@app.get("/ecs/cluster/{cluster_name}")
async def get_cluster_status(cluster_name: str, start_time: datetime = Query(None), end_time: datetime = Query(None)):
    try:
        # Set default time range if not provided
        if not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)

        # Retrieve CloudWatch metrics for the cluster (e.g., CPU and memory utilization)
        cluster_metrics = {}
        for metric_name in ['CPUUtilization', 'MemoryUtilization']:
            metric_data = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name}
                ],
                StartTime=start_time.isoformat(),
                EndTime=end_time.isoformat(),
                Period=300,
                Statistics=['Minimum', 'Maximum', 'Average']
            )
            datapoints = metric_data.get('Datapoints', [])
            cluster_metrics[metric_name] = {
                "Minimum": min(dp.get('Minimum', 0) for dp in datapoints),
                "Maximum": max(dp.get('Maximum', 0) for dp in datapoints),
                "Average": sum(dp.get('Average', 0) for dp in datapoints) / len(datapoints) if datapoints else 0
            }

        # Retrieve Auto Scaling Group (ASG) details (mocked for this example)
        asg_details = {
            "desiredCapacity": 5,
            "runningInstances": 5,
            "pendingInstances": 0
        }

        return {
            "cluster": cluster_name,
            "metrics": cluster_metrics,
            "asgDetails": asg_details
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/ecs/service/{cluster_name}/{service_name}")
async def get_service_status(cluster_name: str, service_name: str, start_time: datetime = Query(None), end_time: datetime = Query(None)):
    try:
        # Set default time range if not provided
        if not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)

        # Retrieve CloudWatch metrics for the service (e.g., CPU and memory utilization)
        service_metrics = {}
        for metric_name in ['CPUUtilization', 'MemoryUtilization']:
            metric_data = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                StartTime=start_time.isoformat(),
                EndTime=end_time.isoformat(),
                Period=300,
                Statistics=['Minimum', 'Maximum', 'Average']
            )
            datapoints = metric_data.get('Datapoints', [])
            service_metrics[metric_name] = {
                "Minimum": min(dp.get('Minimum', 0) for dp in datapoints),
                "Maximum": max(dp.get('Maximum', 0) for dp in datapoints),
                "Average": sum(dp.get('Average', 0) for dp in datapoints) / len(datapoints) if datapoints else 0
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
            "metrics": service_metrics,
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

@app.get("/ecs/task/logs/{cluster_name}/{service_name}")
async def get_task_logs(cluster_name: str, service_name: str):
    try:
        log_group_name = f"/aws/ecs/containerinsights/{cluster_name}/performance"

        # Retrieve log streams with AgentTelemetry prefix
        log_streams = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            logStreamNamePrefix="AgentTelemetry-",
            orderBy="LogStreamName",
            descending=True
        )
        log_streams_info = log_streams.get('logStreams', [])

        if not log_streams_info:
            logging.warning(f"No log streams found for log group {log_group_name}")
            return {"message": "No logs found"}

        # Fetch logs from the most recent log stream
        log_stream_name = log_streams_info[0]['logStreamName']
        log_events = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        return {
            "cluster": cluster_name,
            "service": service_name,
            "log_events": log_events.get('events', [])
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
