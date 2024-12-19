# app.py
from fastapi import FastAPI, HTTPException
import boto3
import os

app = FastAPI()
ecs_client = boto3.client('ecs')

@app.get("/ecs/status/{cluster_name}")
async def get_ecs_status(cluster_name: str):
    try:
        # 取得服務列表
        services = ecs_client.list_services(cluster=cluster_name)
        service_details = ecs_client.describe_services(
            cluster=cluster_name,
            services=services['serviceArns']
        )
        
        # 取得任務列表
        tasks = ecs_client.list_tasks(cluster=cluster_name)
        task_details = []
        if tasks['taskArns']:
            task_details = ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=tasks['taskArns']
            )
        
        return {
            "cluster": cluster_name,
            "services": service_details['services'],
            "tasks": task_details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))