const express = require('express');
const path = require('path');

const web_path = path.join(__dirname, '../public');

module.exports = {
    async init(app){

        app.use(express.static(web_path, {
            extensions: ['html'],
        }));

        app.get('/api', (req, res) => {
            res.redirect('/');
        }); 

        app.get('/:folder', (req, res) => {
            const folderPath = path.join(web_path, req.params.folder, 'index.html');
            res.sendFile(folderPath, (err) => { if (err) res.redirect('/404'); });
        });

    }
}