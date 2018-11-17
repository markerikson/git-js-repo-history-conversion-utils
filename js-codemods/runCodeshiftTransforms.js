const amdToEs6 = require("./amd");
const addNamedExports = require("./named-export-generation");
const varToLetConst = require("./no-vars");
const objectShorthand = require("./object-shorthand");
const trailingCommas = require("./trailing-commas");
const addDefaultExports = require("./addDefaultExportCodemod");


module.exports = function(file, api, options) {
    const fixes = [
        amdToEs6,
        addNamedExports,
        varToLetConst,
        objectShorthand,
        trailingCommas,
        addDefaultExports
    ];

    //const fixes = [addDefaultExports];
    let src = file.source;
    
    fixes.forEach((fix, i) => {
        if (typeof(src) === "undefined") { return; }
        const nextSrc = fix({ ...file, source:src }, api, options);

        if (nextSrc) {
            src = nextSrc;
        }
    });
    return src;
};