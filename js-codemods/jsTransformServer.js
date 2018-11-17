const express = require('express')
const {stopwatch} = require("durations");

const workerpool = require('workerpool');

const app = express()
const port = 4444

// Gotta accept large POSTs
app.use(express.json({limit: '50mb'}));

// Go go multi-core!
const pool = workerpool.pool(__dirname + '/transformJSFile.js', {minWorkers : 8});

app.post('/', async (req, res) => {
    const {body = {}} = req;
    const {commitId, files = []} = body;

    const keys = Object.keys(body);

    if(keys.length === 0 || files.length === 0) {
        res.status(400).send({message : "Invalid request!"});
        return;
    }

    const totalTime = stopwatch();
    totalTime.start();

    console.log(`Request received.  Processing commit ${commitId}...`)

    const transformedFilePromises = files.map(fileEntry => {
        return pool.exec("transformJSFile", [commitId, fileEntry]);
    })

    const transformedFiles = await Promise.all(transformedFilePromises);

    totalTime.stop();
    const totalElapsed = totalTime.duration().seconds();
    console.log(`Processing complete (${totalElapsed}s)\n`);

    res.status(200).send(transformedFiles);

})

app.listen(port, () => console.log(`JS transform server listening on port ${port}!`))