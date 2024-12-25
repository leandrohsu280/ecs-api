const { raw } = require('express');

module.exports = {
    name: 'resource',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post('/api/ecs/resource', async (req, res) => {

            let resdata = { success: true, responce: {}, raw: {} };

            const cloudwatch = new aws.CloudWatch();
            const asg = new aws.AutoScaling();
            const ecs = new aws.ECS();
            const time_end = new Date();
            const time_start = new Date(time_end.getTime() - req.body.timelong * 60 * 60 * 1000);

            const params = { cluster: req.body.cluster, info: req.body.info, time: { start: time_start, end: time_end } };

            await ecs.describeClusters({ clusters: [params.cluster] }, async (err, data) => {
                if (err) {
                    console.log(err, err.stack);
                    resdata = { success: false, message: 'Internal server error' };
                } else {
                    if (data.failures.length > 0) {
                        resdata = { success: false, message: data.failures[0].reason }
                    }
                }
            }).promise()

            if (resdata.success == false) return res.status(500).json(resdata);

            for (const infodata of params.info) {
                const data = await cloudwatch.getMetricStatistics({
                    Namespace: 'AWS/ECS',
                    MetricName: infodata,
                    Dimensions: [
                        { 'Name': 'ClusterName', 'Value': params.cluster }
                    ],
                    StartTime: params.time.start,
                    EndTime: params.time.end,
                    Period: 300,
                    Statistics: ['Average']
                }).promise()

                resdata.raw[infodata] = {};
                resdata.raw[infodata].Datapoints = data.Datapoints.sort((b, a) => new Date(a.Timestamp) - new Date(b.Timestamp));
                let count = 0;
                for (const datapoint of data.Datapoints) {
                    count += datapoint.Average;
                }
                resdata.responce[infodata] = count / data.Datapoints.length;

            }


            res.json(resdata);

        });
    }
}