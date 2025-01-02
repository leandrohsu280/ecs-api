module.exports = {
    name: 'restart-status',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post(app.conf.reqestPath.replace('TYPE', app.path.basename(__dirname)).replace('NAME', this.name), async (req, res) => {

            /* Request Structure

            {
                "cluster": "string", // The name of the ECS cluster
                "serviceName": "string" // The name of the ECS service
            }
            
            */

            const ecs = new aws.ECS();
            const cloudwatch = new aws.CloudWatch();

            const { cluster, serviceName } = req.body;

            if (!cluster || !serviceName) {
                return res.status(400).json({
                    success: false,
                    message: 'Missing required parameters: cluster and serviceName'
                });
            }

            try {
                const taskArns = await ecs.listTasks({
                    cluster,
                    serviceName
                }).promise();

                if (taskArns.taskArns.length === 0) {
                    return res.status(404).json({
                        success: false,
                        message: 'No tasks found for the specified service'
                    });
                }

                const tasks = await ecs.describeTasks({
                    cluster,
                    tasks: taskArns.taskArns
                }).promise();

                const restartCounts = await Promise.all(tasks.tasks.map(async (task) => {
                    const metricData = await cloudwatch.getMetricStatistics({
                        Namespace: 'ECS/ContainerInsights',
                        MetricName: 'ContainerRestartCount',
                        Dimensions: [
                            { Name: 'ClusterName', Value: cluster },
                            { Name: 'TaskId', Value: task.taskArn.split('/').pop() }
                        ],
                        StartTime: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
                        EndTime: new Date().toISOString(),
                        Period: 300,
                        Statistics: ['Sum']
                    }).promise();

                    const restartSum = metricData.Datapoints.reduce((sum, dp) => sum + dp.Sum, 0);

                    return {
                        taskArn: task.taskArn,
                        containerName: task.containers[0]?.name || 'unknown',
                        restartCount: restartSum
                    };
                }));

                res.json({
                    success: true,
                    data: restartCounts
                });

            } catch (err) {
                console.error('Error:', err.stack);
                res.status(500).json({
                    success: false,
                    message: 'Internal server error',
                    error: err.message
                });
            }
        });
    }
}
