from fastapi import FastAPI, HTTPException
import boto3
from typing import Dict, Any

# Initialize the FastAPI app
app = FastAPI()

# AWS Boto3 clients for ECS and CloudWatch
ecs_client = boto3.client('ecs')
cloudwatch_client = boto3.client('cloudwatch')
ec2_client = boto3.client('ec2')
cloudtrail_client = boto3.client('cloudtrail')

@app.get("/ecs/clusters")
def list_ecs_clusters():
    """Fetches the list of ECS clusters."""
    try:
        response = ecs_client.list_clusters()
        return {"clusters": response.get("clusterArns", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ecs/{cluster_name}/services")
def list_services_in_cluster(cluster_name: str):
    """Fetches services in a given ECS cluster."""
    try:
        response = ecs_client.list_services(cluster=cluster_name)
        return {"services": response.get("serviceArns", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ecs/{cluster_name}/tasks")
def list_tasks_in_cluster(cluster_name: str):
    """Fetches tasks running in a given ECS cluster."""
    try:
        response = ecs_client.list_tasks(cluster=cluster_name)
        return {"tasks": response.get("taskArns", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudwatch/metrics")
def list_cloudwatch_metrics(namespace: str):
    """Lists metrics available in CloudWatch for a given namespace."""
    try:
        response = cloudwatch_client.list_metrics(Namespace=namespace)
        return {"metrics": response.get("Metrics", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudwatch/logs")
def get_cloudwatch_logs(log_group_name: str):
    """Fetches CloudWatch logs from a specific log group."""
    try:
        logs_client = boto3.client('logs')
        response = logs_client.describe_log_streams(logGroupName=log_group_name)
        streams = response.get("logStreams", [])
        logs = []
        for stream in streams:
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name, 
                logStreamName=stream["logStreamName"]
            )
            for event in log_events.get("events", []):
                logs.append({
                    "timestamp": event.get("timestamp"),
                    "message": event.get("message")
                })
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudwatch/errors")
def get_cloudwatch_errors(log_group_name: str):
    """Fetches CloudWatch error logs from a specific log group."""
    try:
        logs_client = boto3.client('logs')
        response = logs_client.describe_log_streams(logGroupName=log_group_name)
        streams = response.get("logStreams", [])
        errors = []
        for stream in streams:
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name, 
                logStreamName=stream["logStreamName"]
            )
            for event in log_events.get("events", []):
                message = event.get("message", "")
                if "ERROR" in message.upper():
                    errors.append({
                        "timestamp": event.get("timestamp"),
                        "message": message
                    })
        return {"errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ec2/instances")
def list_ec2_instances():
    """Lists all EC2 instances and their states."""
    try:
        response = ec2_client.describe_instances()
        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append({
                    "InstanceId": instance.get("InstanceId"),
                    "State": instance.get("State", {}).get("Name"),
                    "LaunchTime": instance.get("LaunchTime"),
                    "PublicIpAddress": instance.get("PublicIpAddress"),
                    "PrivateIpAddress": instance.get("PrivateIpAddress"),
                    "InstanceType": instance.get("InstanceType"),
                    "Tags": instance.get("Tags", [])
                })
        return {"instances": instances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ec2/{instance_id}/logs")
def get_instance_logs(instance_id: str):
    """Fetches logs and error codes for a specific EC2 instance."""
    try:
        logs_client = boto3.client('logs')
        log_group_name = f"/aws/ec2/{instance_id}"
        response = logs_client.describe_log_streams(logGroupName=log_group_name)
        streams = response.get("logStreams", [])
        logs = []
        for stream in streams:
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream["logStreamName"]
            )
            for event in log_events.get("events", []):
                logs.append({
                    "timestamp": event.get("timestamp"),
                    "message": event.get("message")
                })
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ec2/{instance_id}/errors")
def get_instance_errors(instance_id: str):
    """Fetches error logs for a specific EC2 instance."""
    try:
        logs_client = boto3.client('logs')
        log_group_name = f"/aws/ec2/{instance_id}"
        response = logs_client.describe_log_streams(logGroupName=log_group_name)
        streams = response.get("logStreams", [])
        errors = []
        for stream in streams:
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream["logStreamName"]
            )
            for event in log_events.get("events", []):
                message = event.get("message", "")
                if "ERROR" in message.upper():
                    errors.append({
                        "timestamp": event.get("timestamp"),
                        "message": message
                    })
        return {"errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudtrail/events")
def get_cloudtrail_events(start_time: str, end_time: str):
    """Fetches CloudTrail events in a specific time range."""
    try:
        response = cloudtrail_client.lookup_events(
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=50
        )
        events = response.get("Events", [])
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudtrail/user-activities")
def get_user_activities(user_name: str):
    """Fetches CloudTrail events for a specific user."""
    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "Username", "AttributeValue": user_name}
            ]
        )
        events = response.get("Events", [])
        return {"user_activities": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloudtrail/errors")
def get_failed_events():
    """Fetches CloudTrail events with failed operations."""
    try:
        response = cloudtrail_client.lookup_events()
        events = response.get("Events", [])
        failed_events = [
            event for event in events if "errorCode" in event.get("CloudTrailEvent", "")
        ]
        return {"failed_events": failed_events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)