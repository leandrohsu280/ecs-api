from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Union
from datetime import datetime, timedelta
import boto3
import pytz
import json

# Initialize FastAPI app
app = FastAPI(title="Enhanced ECS Cluster and Service Status API")

# Initialize AWS clients
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')
logs_client = boto3.client('logs')

# Routes
@app.get("/")
def read_root():
    return {"message": "ECS Cluster and Service Status API is running"}

@app.get("/ecs/cluster/{cluster_name}")
def get_cluster_metrics(
    cluster_name: str,
    start_time: datetime = Query(None),
    end_time: datetime = Query(None)
):
    try:
        if not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)

        metrics = {}
        for metric_name in ["CPUUtilization", "MemoryUtilization"]:
            stats = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName=metric_name,
                Dimensions=[{"Name": "ClusterName", "Value": cluster_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum", "Minimum"]
            )
            datapoints = stats.get("Datapoints", [])
            metrics[metric_name] = {
                "Average": sum(d.get("Average", 0) for d in datapoints) / len(datapoints) if datapoints else 0,
                "Maximum": max(d.get("Maximum", 0) for d in datapoints) if datapoints else 0,
                "Minimum": min(d.get("Minimum", 0) for d in datapoints) if datapoints else 0,
            }

        return {"cluster": cluster_name, "metrics": metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {e}")

@app.get("/ecs/service/{cluster_name}/{service_name}")
def get_service_metrics(
    cluster_name: str,
    service_name: str,
    start_time: datetime = Query(None),
    end_time: datetime = Query(None)
):
    try:
        if not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)

        metrics = {}
        for metric_name in ["CPUUtilization", "MemoryUtilization"]:
            stats = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName=metric_name,
                Dimensions=[
                    {"Name": "ClusterName", "Value": cluster_name},
                    {"Name": "ServiceName", "Value": service_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum", "Minimum"]
            )
            datapoints = stats.get("Datapoints", [])
            metrics[metric_name] = {
                "Average": sum(d.get("Average", 0) for d in datapoints) / len(datapoints) if datapoints else 0,
                "Maximum": max(d.get("Maximum", 0) for d in datapoints) if datapoints else 0,
                "Minimum": min(d.get("Minimum", 0) for d in datapoints) if datapoints else 0,
            }

        return {"cluster": cluster_name, "service": service_name, "metrics": metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {e}")

@app.get("/ecs/task/logs/{cluster_name}/{service_name}")
def get_task_logs(cluster_name: str, service_name: str):
    try:
        log_group_name = f"/aws/ecs/containerinsights/{cluster_name}/performance"
        log_streams = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            logStreamNamePrefix="AgentTelemetry-",
            orderBy="LogStreamName",
            descending=True
        )

        if not log_streams.get("logStreams"):
            return {"cluster": cluster_name, "service": service_name, "logs": []}

        log_stream_name = log_streams["logStreams"][0]["logStreamName"]
        log_events = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )

        taipei_tz = pytz.timezone("Asia/Taipei")
        logs = []
        for event in log_events.get("events", []):
            message = json.loads(event.get("message", "{}"))
            timestamp = datetime.utcfromtimestamp(event["timestamp"] / 1000).astimezone(taipei_tz).isoformat()

            if message.get("Type") == "Task":
                logs.append({
                    "timestamp": timestamp,
                    "task_id": message.get("TaskId"),
                    "task_memory_utilization": message.get("TaskMemoryUtilization"),
                    "storage_read_bytes": message.get("StorageReadBytes"),
                    "storage_write_bytes": message.get("StorageWriteBytes"),
                    "network_rx_bytes": message.get("NetworkRxBytes"),
                    "network_tx_bytes": message.get("NetworkTxBytes"),
                })
            elif message.get("Type") == "Container":
                logs.append({
                    "timestamp": timestamp,
                    "container_name": message.get("ContainerName"),
                    "cpu_utilized": message.get("ContainerCpuUtilized"),
                    "memory_utilized": message.get("ContainerMemoryUtilized"),
                    "network_rx_bytes": message.get("ContainerNetworkRxBytes"),
                    "network_tx_bytes": message.get("ContainerNetworkTxBytes"),
                })

        return {"cluster": cluster_name, "service": service_name, "logs": logs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)