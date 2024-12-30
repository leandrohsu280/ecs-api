from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json
import pytz

# 初始化應用程式
app = FastAPI(title="Enhanced ECS Cluster and Service Status API")

# 初始化 AWS 客戶端
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')
logs_client = boto3.client('logs')

@app.get("/")
def read_root():
    return {"message": "ECS Cluster and Service Status API is running"}

@app.get("/ecs/cluster/{cluster_name}")
async def get_cluster_status(cluster_name: str):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        cluster_metrics = {}
        for metric_name in ['CPUUtilization', 'MemoryUtilization']:
            metric_data = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            cluster_metrics[metric_name] = metric_data.get('Datapoints', [{}])[0].get('Average', 0)

        asg_details = {
            "desiredCapacity": 5,
            "runningInstances": 5,
            "pendingInstances": 0
        }

        return {"cluster": cluster_name, "metrics": cluster_metrics, "asgDetails": asg_details}

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/ecs/service/{cluster_name}/{service_name}")
async def get_service_status(cluster_name: str, service_name: str):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        service_metrics = {}
        for metric_name in ['CPUUtilization', 'MemoryUtilization']:
            metric_data = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            service_metrics[metric_name] = metric_data.get('Datapoints', [{}])[0].get('Average', 0)

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
        log_streams = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            logStreamNamePrefix="AgentTelemetry-",
            orderBy="LogStreamName",
            descending=True
        )
        log_streams_info = log_streams.get('logStreams', [])
        if not log_streams_info:
            return {"message": "No log streams found"}

        log_stream_name = log_streams_info[0]['logStreamName']
        log_events = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )

        taipei_tz = pytz.timezone('Asia/Taipei')
        formatted_logs = []
        for event in log_events.get('events', []):
            message = json.loads(event.get('message', '{}'))
            utc_time = datetime.utcfromtimestamp(event['timestamp'] / 1000)
            local_time = utc_time.astimezone(taipei_tz).isoformat()
            formatted_logs.append({"timestamp": local_time, "message": message})

        return {"cluster": cluster_name, "service": service_name, "log_events": formatted_logs}

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)