module.exports = {
    name: 'cluster',

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
                "eventLimit": number // Optional, number of events to return per service
            }
            
            */

            const ecs = new aws.ECS();
            const params = { clusters: [req.body.cluster] };
            const eventLimit = req.body.eventLimit || 5;

            try {
                const clusterData = await ecs.describeClusters(params).promise();

                if (clusterData.failures.length > 0) {
                    return res.status(500).json({
                        success: false,
                        data: {
                            reason: clusterData.failures[0]?.reason || 'Unknown reason',
                            arn: clusterData.failures[0]?.arn || 'Unknown ARN'
                        }
                    });
                }

                const clusterInfo = clusterData.clusters[0];
                const servicesParams = {
                    cluster: clusterInfo.clusterName
                };
                const servicesData = await ecs.listServices(servicesParams).promise();
                const services = await Promise.all(
                    servicesData.serviceArns.map(async (serviceArn) => {
                        const serviceData = await ecs.describeServices({
                            cluster: clusterInfo.clusterName,
                            services: [serviceArn]
                        }).promise();

                        return serviceData.services.map(service => ({
                            serviceArn: formatArn(service.serviceArn),
                            serviceName: service.serviceName,
                            status: service.status,
                            desiredCount: service.desiredCount,
                            runningCount: service.runningCount,
                            pendingCount: service.pendingCount,
                            taskDefinition: formatArn(service.taskDefinition),
                            createdBy: formatIAMArn(service.createdBy),
                            createdAt: service.createdAt,
                            deployments: service.deployments.map(deployment => ({
                                id: deployment.id,
                                status: deployment.status,
                                createdAt: deployment.createdAt,
                                updatedAt: deployment.updatedAt,
                                rolloutState: deployment.rolloutState,
                                rolloutStateReason: deployment.rolloutStateReason
                            })),
                            events: service.events.slice(0, eventLimit).map(event => ({
                                id: event.id,
                                createdAt: event.createdAt,
                                message: event.message
                            }))
                        }));
                    })
                );

                res.json({
                    success: true,
                    data: {
                        cluster: {
                            clusterArn: formatArn(clusterInfo.clusterArn),
                            clusterName: clusterInfo.clusterName,
                            status: clusterInfo.status,
                            registeredContainerInstancesCount: clusterInfo.registeredContainerInstancesCount,
                            runningTasksCount: clusterInfo.runningTasksCount,
                            pendingTasksCount: clusterInfo.pendingTasksCount,
                            activeServicesCount: clusterInfo.activeServicesCount,
                            createdBy: formatIAMArn(clusterInfo.createdBy),
                            createdAt: clusterInfo.createdAt
                        },
                        services: services.flat()
                    }
                });

            } catch (err) {
                console.error('Error:', err.stack);
                res.status(500).json({
                    success: false,
                    data: { message: 'Internal server error', error: err.message }
                });
            }
        });
    }
}

function formatArn(input) {
    if (!input || typeof input !== 'string' || !input.includes(':')) {
        return { error: 'Invalid ARN format' };
    }

    const parts = input.split(':');
    const resourceParts = parts[5]?.split('/') || [];

    return {
        partition: parts[1] || 'unknown',
        service: parts[2] || 'unknown',
        region: parts[3] || 'unknown',
        account: parts[4] || 'unknown',
        resource: {
            service: resourceParts[0] || 'unknown',
            name: resourceParts[1] || 'unknown'
        }
    };
}

function formatIAMArn(input) {
    if (!input || typeof input !== 'string' || !input.includes(':')) {
        return { error: 'Invalid ARN format' };
    }

    const parts = input.split(':');
    const pathParts = parts[5]?.split('/') || [];

    return {
        partition: parts[1] || 'unknown',
        service: parts[2] || 'unknown',
        region: parts[3] || 'unknown',
        account: parts[4] || 'unknown',
        rolePath: pathParts.slice(0, -1).join('/') || 'unknown',
        roleName: pathParts.slice(-1)[0] || 'unknown'
    };
}
