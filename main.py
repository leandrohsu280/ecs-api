from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Enhanced ECS Cluster and Service Status API")
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')

class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime

def get_metric_statistics(namespace, metric_name, dimensions, start_time, end_time, period=300):
    try:
        response = cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time.isoformat(),
            EndTime=end_time.isoformat(),
            Period=period,
            Statistics=['Minimum', 'Maximum', 'Average']
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            logging.warning(f"No data points found for {metric_name} with dimensions {dimensions}")
        return datapoints
    except (BotoCoreError, ClientError) as e:
        logging.error(f"Error fetching metric statistics: {e}")
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/")
def root():
    return {"message": "Welcome to ECS Cluster and Service Status API"}

@app.get("/ecs/status/{cluster_name}")
def ecs_cluster_status(cluster_name: str, time_range: TimeRange):
    start_time = time_range.start_time
    end_time = time_range.end_time

    asg_dimensions = [{'Name': 'ClusterName', 'Value': cluster_name}]

    cpu_data = get_metric_statistics(
        namespace="AWS/ECS",
        metric_name="CPUUtilization",
        dimensions=asg_dimensions,
        start_time=start_time,
        end_time=end_time
    )

    memory_data = get_metric_statistics(
        namespace="AWS/ECS",
        metric_name="MemoryUtilization",
        dimensions=asg_dimensions,
        start_time=start_time,
        end_time=end_time
    )

    return {
        "cluster_name": cluster_name,
        "cpu_utilization": cpu_data,
        "memory_utilization": memory_data
    }

@app.get("/ecs/status/{cluster_name}/{service_name}")
def ecs_service_status(cluster_name: str, service_name: str, time_range: TimeRange):
    start_time = time_range.start_time
    end_time = time_range.end_time

    service_dimensions = [
        {'Name': 'ClusterName', 'Value': cluster_name},
        {'Name': 'ServiceName', 'Value': service_name}
    ]

    cpu_data = get_metric_statistics(
        namespace="AWS/ECS",
        metric_name="CPUUtilization",
        dimensions=service_dimensions,
        start_time=start_time,
        end_time=end_time
    )

    memory_data = get_metric_statistics(
        namespace="AWS/ECS",
        metric_name="MemoryUtilization",
        dimensions=service_dimensions,
        start_time=start_time,
        end_time=end_time
    )

    return {
        "cluster_name": cluster_name,
        "service_name": service_name,
        "cpu_utilization": cpu_data,
        "memory_utilization": memory_data
    }

@app.get("/ecs/task/logs")
def ecs_task_logs(cluster_name: str, service_name: str):
    log_group_name = f"/aws/ecs/containerinsights/{cluster_name}/performance"

    try:
        log_streams = cloudwatch_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True
        )
        log_streams_info = log_streams.get('logStreams', [])

        if not log_streams_info:
            logging.warning(f"No log streams found for log group {log_group_name}")
            return {"message": "No logs found"}

        log_stream_name = log_streams_info[0]['logStreamName']
        log_events = cloudwatch_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        return log_events.get('events', [])
    except (BotoCoreError, ClientError) as e:
        logging.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)