module.exports = {
    name: 'logs',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post(app.conf.reqestPath.replace('TYPE', app.path.basename(__dirname)).replace('NAME', this.name), async (req, res) => {

            /* Request Structure
            
            {
                "logGroupName": "string",
                "logStreamName": "string",
                "timeRange": number,
                "limit": number
            }
            
            */

            const clientData = req.body;
            let resdata = { success: true, responce: {} };

            const cloudwatchlogs = new aws.CloudWatchLogs();
            const now = Date.now();
            const params = {
                logGroupName: clientData.logGroupName,
                logStreamName: clientData.logStreamName,
                startTime: now - 1000 * 60 * 60 * req.body.timeRange,
                endTime: now,
                limit: req.body.limit
            };

            try {
                const data = await cloudwatchlogs.getLogEvents(params).promise();

                if (data.events && data.events.length > 0) {
                    resdata.responce = data.events.map(event => {
                        if (!event.message) return { message: 'No message' };

                        const format = event.message.split(' ');
                        const formattedTime = formatTimestamp(event.timestamp);

                        const eventData = {
                            version: format[0],
                            accountId: format[1],
                            interfaceId: format[2],
                            srcaddr: format[3],
                            dstaddr: format[4],
                            srcport: format[5],
                            dstport: format[6],
                            protocol: format[7],
                            packets: format[8],
                            bytes: format[9],
                            start: format[10],
                            end: format[11],
                            action: format[12],
                            logStatus: format[13]
                        };

                        return {
                            ingestionTime: formattedTime,
                            timestamp: formattedTime,
                            messages: eventData,
                        };
                    });
                } else {
                    resdata.success = false;
                    resdata.responce = { message: 'No log events found' };
                }
            } catch (err) {
                return res.status(500).json({
                    success: false,
                    responce: { message: err.message },
                });
            }

            res.json(resdata);
        });
    }
};

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}
