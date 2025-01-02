module.exports = {
    name: 'custom-metric',

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
                "metric": "string", // The name of the metric to analyze (e.g., CPUUtilization, MemoryUtilization)
                "startTime": "ISO string", // Start time for the historical trend
                "endTime": "ISO string", // End time for the historical trend
                "period": number // Period for data points in seconds
            }
            
            */

            const cloudwatch = new aws.CloudWatch();

            const { cluster, metric, startTime, endTime, period } = req.body;

            if (!cluster || !metric || !startTime || !endTime || !period) {
                return res.status(400).json({
                    success: false,
                    message: 'Missing required parameters: cluster, metric, startTime, endTime, and period'
                });
            }

            try {
                const metricData = await cloudwatch.getMetricStatistics({
                    Namespace: 'AWS/ECS',
                    MetricName: metric,
                    Dimensions: [
                        { Name: 'ClusterName', Value: cluster }
                    ],
                    StartTime: new Date(startTime).toISOString(),
                    EndTime: new Date(endTime).toISOString(),
                    Period: period,
                    Statistics: ['Average', 'Maximum', 'Minimum']
                }).promise();

                const trend = metricData.Datapoints.map(dp => ({
                    timestamp: dp.Timestamp,
                    average: dp.Average || 0,
                    maximum: dp.Maximum || 0,
                    minimum: dp.Minimum || 0
                })).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

                res.json({
                    success: true,
                    data: {
                        cluster,
                        metric,
                        trend
                    }
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
