Build API Server on AWS App Runner to monitor ECS Service - overall

1.Open AWS App Runner Website

2.Create Service

3.Select "Source code repository" and "Provider - GitHub"

4.Choose repository contain "Dockerfile, main.py and requirements.txt"

5.Next page for build setting click "Python3 for runtime", type "pip install -r requirements.txt" on build command and "uvicorn main:app --host 0.0.0.0 --port 8080" on start command.
  Default port is 8080 which may also be changed from your modified port on main.py

6.Desire your service name, vCpu and vMemory based on your startegy.

7.Access role for this app runner which means you should access your service (e.g. full access ecs) for app runner to allow server to read data.

8.Next page for checking your setting of app runner.

9.Wait for building server.

10.Click the default domain and you can see "api is running" if success.
