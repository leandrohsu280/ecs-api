module.exports = {
    name: 'cpu',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post(app.conf.reqestPath.replace('TYPE', app.path.basename(__dirname)).replace('NAME', this.name), async (req, res) => {

            /* Request Structure
            
            {
                "cluster": "string",
                "time": "2d" | "1hr" | "20min" | "60sec" | "YYYY/MM/DD-YYYY/MM/DD" | "HH:mm-HH:mm",
                "limit": number // Optional, maximum number of data points to return
            }
            
            */

            let resdata = { success: true, response: {}, raw: {} };

            const cloudwatch = new aws.CloudWatch();
            const ecs = new aws.ECS();

            let time_end = new Date();
            let time_start = new Date();

            try {
                const timePattern = /^\d+(d|hr|min|sec)$/;
                const rangePattern = /^\d{4}\/\d{2}\/\d{2}-\d{4}\/\d{2}\/\d{2}$/;
                const todayTimePattern = /^\d{1,2}:\d{2}-\d{1,2}:\d{2}$/;

                if (timePattern.test(req.body.time)) {
                    const match = req.body.time.match(/(\d+)(d|hr|min|sec)/);
                    const value = parseInt(match[1]);
                    const unit = match[2];

                    switch (unit) {
                        case 'd':
                            time_start = new Date(time_end.getTime() - value * 24 * 60 * 60 * 1000);
                            break;
                        case 'hr':
                            time_start = new Date(time_end.getTime() - value * 60 * 60 * 1000);
                            break;
                        case 'min':
                            time_start = new Date(time_end.getTime() - value * 60 * 1000);
                            break;
                        case 'sec':
                            time_start = new Date(time_end.getTime() - value * 1000);
                            break;
                    }
                } else if (rangePattern.test(req.body.time)) {
                    const [start, end] = req.body.time.split('-');
                    time_start = new Date(`${start}T00:00:00`);
                    time_end = new Date(`${end}T23:59:59`);

                    if (time_start >= time_end) {
                        return res.status(400).json({ success: false, message: 'Start time must be before end time' });
                    }
                } else if (todayTimePattern.test(req.body.time)) {
                    const [start, end] = req.body.time.split('-');
                    const today = new Date().toISOString().split('T')[0];
                    time_start = new Date(`${today}T${start}:00`);
                    time_end = new Date(`${today}T${end}:00`);

                    if (time_start >= time_end) {
                        return res.status(400).json({ success: false, message: 'Start time must be before end time' });
                    }
                } else {
                    return res.status(400).json({ success: false, message: 'Invalid time format provided' });
                }
            } catch (e) {
                return res.status(400).json({ success: false, message: 'Error parsing time field' });
            }

            const params = { cluster: req.body.cluster, time: { start: time_start, end: time_end } };

            try {
                const clusterData = await ecs.describeClusters({ clusters: [params.cluster] }).promise();

                if (clusterData.failures.length > 0) {
                    return res.status(500).json({ success: false, message: clusterData.failures[0].reason });
                }

                // Adjust the time range if too many data points are requested
                const requestedRangeMs = time_end - time_start;
                const maxDataPoints = req.body.limit || 100;
                const period = Math.ceil(requestedRangeMs / (maxDataPoints * 1000));

                const metricData = await cloudwatch.getMetricStatistics({
                    Namespace: 'AWS/ECS',
                    MetricName: 'CPUUtilization',
                    Dimensions: [
                        { Name: 'ClusterName', Value: params.cluster }
                    ],
                    StartTime: time_start.toISOString(),
                    EndTime: time_end.toISOString(),
                    Period: period < 60 ? 60 : period, // Ensure minimum period is 60 seconds
                    Statistics: ['Average', 'Maximum', 'Minimum']
                }).promise();

                resdata.raw['CPUUtilization'] = {
                    Datapoints: metricData.Datapoints.sort((a, b) => new Date(b.Timestamp) - new Date(a.Timestamp))
                };

                if (req.body.limit && resdata.raw['CPUUtilization'].Datapoints.length > req.body.limit) {
                    resdata.raw['CPUUtilization'].Datapoints = resdata.raw['CPUUtilization'].Datapoints.slice(0, req.body.limit);
                }

                const totalAverage = metricData.Datapoints.reduce((sum, datapoint) => sum + datapoint.Average, 0);
                const totalMax = metricData.Datapoints.reduce((max, datapoint) => Math.max(max, datapoint.Maximum), 0);
                const totalMin = metricData.Datapoints.reduce((min, datapoint) => Math.min(min, datapoint.Minimum), Infinity);

                resdata.response['CPUUtilization'] = {
                    Average: metricData.Datapoints.length > 0 ? totalAverage / metricData.Datapoints.length : 0,
                    Maximum: totalMax,
                    Minimum: totalMin,
                    Trend: resdata.raw['CPUUtilization'].Datapoints.map(dp => ({
                        Timestamp: dp.Timestamp,
                        Value: dp.Average
                    }))
                };

                res.json(resdata);

            } catch (err) {
                console.error('Error:', err.stack);
                res.status(500).json({ success: false, message: 'Internal server error', error: err.message });
            }
        });
    }
}
