from fastapi import FastAPI, HTTPException

app = FastAPI(title="ECS Status API")

@app.get("/")
def read_root():
    return {"message": "ECS Status API is running"}

@app.get("/ecs/status/{cluster_name}")
async def get_ecs_status(cluster_name: str):
    return {
        "cluster": cluster_name,
        "services": [
            {"serviceName": "dummy-service", "desiredCount": 1, "runningCount": 1, "status": "ACTIVE"}
        ],
        "tasks": [
            {"taskArn": "dummy-task", "lastStatus": "RUNNING", "desiredStatus": "RUNNING"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
