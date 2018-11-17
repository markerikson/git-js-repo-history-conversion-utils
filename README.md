# Git and JS History Conversion Tools

These tools accompany my blog post [Rewriting Your Git History and JS Source for Fun and Profit](https://blog.isquaredsoftware.com/2018/11/git-js-history-rewriting/).

They are a slightly sanitized version of the scripts that I used to rewrite our Git repository, by converting all AMD/ES5 code to ES6 module syntax, and auto-formatting all JS and Python source throughout the entire history of the repository.

If you actually wanted to use this:

**Setup**
1. Tweak paths as needed:
    1. Edit `repoFilterUtils.py` to define the source repo and output repo paths
    2. Edit `js-codemods/transformJSFile.js` and fix the path to a temp folder for writing errors to disk
2. Use `yarn` to install the JS dependencies under `js-codemods/`
3. Install Black and Requests into your system's Python3 location

**Running**

1. Run `node js-codemods/jsTransformServer` in a separate shell.
2. Run `python3 cloneAndProcessRepo.py` to kick this off.

