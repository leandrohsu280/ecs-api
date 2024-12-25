const express = require('express');
const app = require('express')();
const aws = require('aws-sdk');
require('aws-sdk/lib/maintenance_mode_message').suppress = true;

// const config = require('./env.json')

const api_init = require('./api/init.js')
const web_init = require('./public/init.js')

// aws.config.update({
//     accessKeyId: config.accesskey,
//     secretAccessKey: config.secretkey,
//     region: config.region
// })


function start(){

    app.express = express;

    api_init.init(app, aws);
    web_init.init(app);

    // app.listen(config.serverPort, () => {
    app.listen(8080, () => {
        console.log(`Server started on port 8080`);
    })
}

start();