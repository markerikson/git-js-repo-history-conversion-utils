const fs= require("fs");

const transform = require('babel-core').transform;
const recast = require('recast');
const addDefaultExportTransform = require('./babel-plugin-add-default-exports');

const babelOptionsText = fs.readFileSync("./.babelrc");
const babelOptions = JSON.parse(babelOptionsText);

// Turn a Babel plugin into a jscodeshift transform
module.exports = function(fileInfo, api, options) {
    return transform(fileInfo.source, {
        parserOpts: {
            parser: recast.parse,
            // Parse all the syntax we actually use
            plugins : ["jsx", "flow", "classProperties", "dynamicImport", "objectRestSpread"]
        },
        generatorOpts: {
            generator: recast.print
        },
        // Only apply this transformation
        plugins: [addDefaultExportTransform]
    }).code;
};