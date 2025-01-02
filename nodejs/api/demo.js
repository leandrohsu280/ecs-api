module.exports = {
    name: 'name',

    /**
     * @param {import('express').Application} app
     * @param {import('aws-sdk')} aws
     */

    async execute(app, aws) {

        app.use(app.express.json());

        app.post(app.conf.reqestPath.replace('TYPE', app.path.basename(__dirname)).replace('NAME', this.name), async (req, res) => {

            /* Request Structure

            {
                
            }
            
            */

            
        });
    }
}