from fastapi import FastAPI, HTTPException
import boto3

app = FastAPI(title="ECS Status API")
ecs_client = boto3.client('ecs')

@app.get("/")
def read_root():
    return {"message": "ECS Status API is running"}

@app.get("/ecs/status/{cluster_name}")
async def get_ecs_status(cluster_name: str):
    try:
        # Retrieve services
        services = ecs_client.list_services(cluster=cluster_name)
        service_details = ecs_client.describe_services(
            cluster=cluster_name,
            services=services['serviceArns']
        )

        # Retrieve tasks
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)