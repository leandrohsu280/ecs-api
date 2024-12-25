from fastapi import FastAPI, HTTPException
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta

app = FastAPI(title="ECS Cluster and Service Status API")
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')

@app.get("/")
def read_root():
    return {"message": "ECS Cluster and Service Status API is running"}

@app.get("/ecs/cluster/{cluster_name}")
async def get_cluster_status(cluster_name: str):
    try:
        # Calculate time range for CloudWatch metrics
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
                Statistics=['Average']
            )
            cluster_metrics[metric_name] = metric_data.get('Datapoints', [{}])[0].get('Average', 0)

        # Retrieve Auto Scaling Group (ASG) details (mocked for this example)
        # Integration with ASG API or tagging strategies would be needed for real-world use
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
async def get_service_status(cluster_name: str, service_name: str):
    try:
        # Calculate time range for CloudWatch metrics
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
                Statistics=['Average']
            )
            service_metrics[metric_name] = metric_data.get('Datapoints', [{}])[0].get('Average', 0)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)