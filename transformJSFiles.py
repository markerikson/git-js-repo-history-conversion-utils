import re
import sys, os
from pathlib import Path
import shutil, tempfile
from unicodedata import normalize

# Make Requests ignore any system proxy settings
os.environ["no_proxy"] = "*"

import requests
from plumbum import local


from repoFilterUtils import update, replaceEntry, normalizeEntry

FILES_TO_SKIP = ["someSpecificFile.js"]


SYNTAX_FIXES = {
    "App1/src/file1.js" : [
        (
            re.compile(r'some specific regex here', re.MULTILINE | re.DOTALL),
            r"some specific regex sub pattern here"
        )
    ],
    "App1/src/file2.js": [
        (
            "look for this string",
            "replace with this string"
        )
    ]
}



def find(f, seq):
  """Return first item in sequence where f(item) == True."""
  for item in seq:
    if f(item):
      return item

def findFileByName(fileName):
    def findCallback(fileEntry):
        path = Path(fileEntry["name"])
        return path.match("*" + fileName)

    return findCallback




def replaceUnicodeCharacters(jsFilesList):
    return list(map(normalizeEntry, jsFilesList))

def replaceContent(fileEntry, searchText, replaceText):
    source = fileEntry["source"]

    if isinstance(searchText, re.Pattern):
        newText = searchText.sub(replaceText, source)
    else:
        newText = source.replace(searchText, replaceText)
    return update(fileEntry, {"source" : newText})


def replaceDynamicImports(jsFilesList):
    entryPoint = find(findFileByName("entryPoint.js"), jsFilesList)

    newFilesList = jsFilesList

    if (entryPoint):
        newFileEntry = replaceContent(entryPoint, "import(", "require.ensure(")
        newFilesList = replaceEntry(jsFilesList, entryPoint, newFileEntry)

    return newFilesList

def undoReplaceDynamicImports(jsFilesList):
    entryPoint = find(findFileByName("entryPoint.js"), jsFilesList)

    newFilesList = jsFilesList

    if (entryPoint):
        newFileEntry = replaceContent(entryPoint, "require.ensure(", "import(")
        newFilesList = replaceEntry(jsFilesList, entryPoint, newFileEntry)

    return newFilesList


def removeConvertedRequireImports(jsFilesList):
    newFilesList = jsFilesList
    for filename in ["entryPoint.js", "largeChunk.js", "smallChunk.js"]:
        fileEntry = find(findFileByName(filename), newFilesList)

        if(fileEntry):
            newFileEntry = replaceContent(fileEntry, 'import require from "require";', "")
            newFilesList = replaceEntry(newFilesList, fileEntry, newFileEntry)

    return newFilesList



def fixInvalidSyntax(jsFilesList):
    fileFixes = SYNTAX_FIXES.items()

    newFilesList = jsFilesList

    for fileEntry in jsFilesList:
        fileName = fileEntry["name"]

        for badFileName, fixes in fileFixes:
            if fileName.endswith(badFileName):
                newFileEntry = fileEntry
                for searchText, replaceText in fixes:
                    newFileEntry = replaceContent(newFileEntry, searchText, replaceText)
                newFilesList = replaceEntry(newFilesList, fileEntry, newFileEntry)


    return newFilesList

def filterFilesToBeSkipped(jsFilesList):
    skippedList = []
    newJsFilesList = []

    for fileEntry in jsFilesList:
        fileName = fileEntry["name"]

        shouldSkip = any([fileName.endswith(fileToSkip) for fileToSkip in FILES_TO_SKIP])


        if shouldSkip:
            skippedList.append(fileEntry)
        else:
            newJsFilesList.append(fileEntry)

    return (skippedList, newJsFilesList)



def transformJSFiles(commitId, jsFilesList):
    for fileEntry in jsFilesList:

        fileSource = fileEntry["source"]
        isApp2SourceFile = fileEntry["name"].startswith("App2")

        fileEntry["formatOnly"] = isApp2SourceFile

    request = {"commitId" : commitId, "files" : jsFilesList}
    response = requests.post("http://localhost:4444", json=request)
    transformedFiles = response.json()
    return transformedFiles


def rewriteAvailableJSFiles(commitId, jsFilesList):
    jsFilesList = replaceUnicodeCharacters(jsFilesList)
    skippedList, jsFilesList = filterFilesToBeSkipped(jsFilesList)

    if not jsFilesList:
        return []


    jsFilesList = replaceDynamicImports(jsFilesList)
    jsFilesList = fixInvalidSyntax(jsFilesList)
    jsFilesList = transformJSFiles(commitId, jsFilesList)
    jsFilesList = removeConvertedRequireImports(jsFilesList)
    jsFilesList = undoReplaceDynamicImports(jsFilesList)

    totalResults = skippedList + jsFilesList
    return totalResults


def main():
    rewriteAvailableJSFiles([])

if __name__ == "__main__":
    main()