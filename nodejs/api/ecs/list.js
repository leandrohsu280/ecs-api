module.exports = {
    name: 'list',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post(app.conf.reqestPath.replace('TYPE', app.path.basename(__dirname)).replace('NAME', this.name), async (req, res) => {

            /* Request Structure

            {
                // No additional parameters required for this endpoint
            }

            */

            const ecs = new aws.ECS();

            try {
                // List all ECS clusters
                const clustersData = await ecs.listClusters().promise();
                const clusters = clustersData.clusterArns;

                if (clusters.length === 0) {
                    return res.json({
                        success: true,
                        data: []
                    });
                }

                // Fetch services for each cluster
                const clustersWithServices = await Promise.all(
                    clusters.map(async (clusterArn) => {
                        const clusterName = clusterArn.split('/').pop();
                        const servicesData = await ecs.listServices({ cluster: clusterArn }).promise();

                        const servicesDetails = await Promise.all(
                            servicesData.serviceArns.map(async (serviceArn) => {
                                const serviceData = await ecs.describeServices({
                                    cluster: clusterArn,
                                    services: [serviceArn]
                                }).promise();

                                return serviceData.services.map(service => ({
                                    serviceArn: service.serviceArn,
                                    serviceName: service.serviceName,
                                    status: service.status,
                                    desiredCount: service.desiredCount,
                                    runningCount: service.runningCount,
                                    pendingCount: service.pendingCount
                                }));
                            })
                        );

                        return {
                            clusterArn,
                            clusterName,
                            services: servicesDetails.flat()
                        };
                    })
                );

                res.json({
                    success: true,
                    data: clustersWithServices
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
