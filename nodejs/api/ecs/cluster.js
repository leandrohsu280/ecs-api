module.exports = {
    name: 'cluster',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post('/api/ecs/cluster', async (req, res) => {

            let resdata = {}
            const ecs = new aws.ECS();
            const params = { clusters: [req.body.cluster] };

            await ecs.describeClusters(params, async (err, data) => {
                if (err) {
                    console.log(err, err.stack);
                    res.status(500).json({ message: 'Internal server error' });
                } else {

                    resdata = {
                        success: data.failures.length == 0 ? true : false,
                        response: data.failures.length == 0 ? data.clusters[0] : data.failures[0]
                    }
                    
                }
            }).promise()

            res.json(resdata);

        });
    }
}