const express = require('express');
const app = require('express')();
const aws = require('aws-sdk');
require('aws-sdk/lib/maintenance_mode_message').suppress = true;


const api_init = require('./api/init.js')
const web_init = require('./public/init.js')

const conf = require('./config.json')

//==========config

const config = require('./env.json')
aws.config.update({
    accessKeyId: config.accesskey,
    secretAccessKey: config.secretkey,
    region: config.region
})

//==========config


function start(){

    app.express = express;
    app.conf = conf;

    api_init.init(app, aws);
    web_init.init(app);

    // app.listen(config.serverPort, () => {
    app.listen(8080, () => {
        console.log(`Server started on port 8080`);
    })
}

start();

//don't kill process after error

process.on('uncaughtException', function (err) {
    console.log(err);
});