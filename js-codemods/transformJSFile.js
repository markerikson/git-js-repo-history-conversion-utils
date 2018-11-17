const fs = require("fs");
const path = require("path");

const {stopwatch} = require("durations");

const mkdirp = require("mkdirp");
const serializeError = require("serialize-error");
const workerpool = require('workerpool');

const jscodeshiftCore = require("jscodeshift");
const prettier = require("prettier");

const transform = require("./runCodeshiftTransforms");

const ERROR_OUTPUT_PATH = "$TEMP/js-transform-errors";

function empty() {}

const jscodeshift = jscodeshiftCore.withParser("babel");

const prettierOptions = {
	"printWidth" : 120,
	"tabWidth" : 4,
	"useTabs" : false,
	"semi" : true,
	"singleQuote" : false,
	"trailingComma" : "all",
	"bracketSpacing" : false,
	"jsxBracketSameLine" : false,
	"arrowParens" : "avoid",
    "parser" : "babylon",
};



function runJscodeshiftTransform(fileEntry) {
    const {name : file, source} = fileEntry;
    const transformedSource = transform(
            { path: file, source: source, },
            {j: jscodeshift,jscodeshift, stats: empty},
            {}
        );
    return transformedSource;
}

function replaceExt(npath, ext) {
  if (typeof npath !== 'string') {
    return npath;
  }

  if (npath.length === 0) {
    return npath;
  }

  const nFileName = path.basename(npath, path.extname(npath)) + ext;
  return path.join(path.dirname(npath), nFileName);
}

function saveErrorLog(commitId, fileEntry, error) {
    const outputFolder = path.join(ERROR_OUTPUT_PATH, commitId.slice(0, 8));
    mkdirp.sync(outputFolder);

    const {name, source, hash} = fileEntry;
    const fileName = path.basename(name);

    const outputFilename = `${hash}_${fileName}`;

    const fileSourcePath = path.join(outputFolder, outputFilename);
    fs.writeFileSync(fileSourcePath, fileEntry.source);

    const extension = path.extname(outputFilename);
    const errorFilename = outputFilename.replace(extension, ".json");
    const fileErrorPath = path.join(outputFolder, errorFilename);

    const serializedError = serializeError(error);
    const jsonOutput = JSON.stringify(serializedError);
    fs.writeFileSync(fileErrorPath, jsonOutput);
}


function transformJSSource(commitId, fileEntry) {
    const {source, name, hash, formatOnly = false} = fileEntry;
    let finalSource = source;
    let failedSource;

    console.log(`Processing file (${hash}): ${name}`);

    try {
        //console.log("Transforming file: " + fileEntry.name);
        if(!formatOnly) {
            finalSource = runJscodeshiftTransform(fileEntry);
        }

        //console.log("Formatting file: " + fileEntry.name)
        finalSource = prettier.format(finalSource, prettierOptions);
    }
    catch(e) {
        console.error(e);
        failedSource = finalSource;
        finalSource = source;

        saveErrorLog(commitId, fileEntry, e);
    }

    return [finalSource, failedSource];
}

function transformJSFile(commitId, fileEntry) {
    const fileTime = stopwatch();
    fileTime.start();

    const [transformedSource, failedSource] = transformJSSource(commitId, fileEntry);

    fileTime.stop();
    const fileElapsed = fileTime.duration().seconds();

    console.log(`Completed file (${fileElapsed}s): ${fileEntry.name}`);
    return {
        ...fileEntry,
        source : transformedSource,
        failedSource
    };
}


workerpool.worker({
  transformJSFile
});
