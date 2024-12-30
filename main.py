from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Union
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta, timezone
import pytz
import json
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Enhanced ECS Cluster and Service Status API")

# AWS Clients
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')
logs_client = boto3.client('logs')

# Schemas
class ContainerLog(BaseModel):
    timestamp: str
    container_name: Optional[str]
    task_id: str
    cpu_utilized: Optional[float]
    memory_utilized: Optional[int]
    memory_utilization: Optional[float]
    storage_read_bytes: Optional[int]
    storage_write_bytes: Optional[int]
    network_rx_bytes: Optional[int]
    network_tx_bytes: Optional[int]

class TaskLog(BaseModel):
    timestamp: str
    task_id: str
    service_name: str
    cluster_name: str
    task_definition: str
    known_status: str
    cpu_reserved: Optional[float]
    memory_reserved: Optional[int]
    started_at: Optional[str]

class LogEventResponse(BaseModel):
    cluster: str
    service: str
    container_logs: List[ContainerLog]
    task_logs: List[TaskLog]

@app.get("/")
def read_root():
    return {"message": "ECS Cluster and Service Status API is running"}

@app.get("/ecs/task/logs/{cluster_name}/{service_name}", response_model=LogEventResponse)
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

        taipei_tz = pytz.timezone('Asia/Taipei')
        container_logs = []
        task_logs = []

        for event in log_events.get('events', []):
            message = json.loads(event.get('message', '{}'))
            utc_time = datetime.utcfromtimestamp(event['timestamp'] / 1000).replace(tzinfo=timezone.utc)
            local_time = utc_time.astimezone(taipei_tz).isoformat()

            if message.get("Type") == "Container":
                container_logs.append(ContainerLog(
                    timestamp=local_time,
                    container_name=message.get("ContainerName"),
                    task_id=message.get("TaskId"),
                    cpu_utilized=message.get("ContainerCpuUtilized"),
                    memory_utilized=message.get("ContainerMemoryUtilized"),
                    memory_utilization=message.get("ContainerMemoryUtilization"),
                    storage_read_bytes=message.get("ContainerStorageReadBytes"),
                    storage_write_bytes=message.get("ContainerStorageWriteBytes"),
                    network_rx_bytes=message.get("ContainerNetworkRxBytes"),
                    network_tx_bytes=message.get("ContainerNetworkTxBytes")
                ))
            elif message.get("Type") == "Task":
                task_logs.append(TaskLog(
                    timestamp=local_time,
                    task_id=message.get("TaskId"),
                    service_name=message.get("ServiceName"),
                    cluster_name=message.get("ClusterName"),
                    task_definition=f"{message.get('TaskDefinitionFamily')}:{message.get('TaskDefinitionRevision')}",
                    known_status=message.get("KnownStatus"),
                    cpu_reserved=message.get("CpuReserved"),
                    memory_reserved=message.get("MemoryReserved"),
                    started_at=datetime.utcfromtimestamp(message.get("StartedAt") / 1000).astimezone(taipei_tz).isoformat() if message.get("StartedAt") else None
                ))

        return {
            "cluster": cluster_name,
            "service": service_name,
            "container_logs": container_logs,
            "task_logs": task_logs
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
