import shutil
from unicodedata import normalize
import tempfile
from pathlib import Path

SOURCE_REPO_PATH = Path("path/to/source/repo")
OUTPUT_REPO_PATH = Path("path/to/output/repo")


APP1_SOURCE_PATH = Path("App1/src")
APP2_SOURCE_PATH = Path("App2/client/src")

JS_SOURCE_PATHS = set([APP1_SOURCE_PATH, APP2_SOUREC_PATH])

PYTHON_SERVICES = ["PythonService1", "PythonService2"]

EXTRA_PYTHON_SOURCE_SUBFOLDERS = {
    "PythonService1" : ["utils"],
    "PythonService2" : ["feature1"],
}


PYTHON_FILES_TO_IGNORE = ["bottle.py", "argparse.py", "setup.py", "six.py"]

JS_LIBS_TO_IGNORE = ["jquery", "hammer", "moment", "libraries"]


def writeTempBlob(fileBlob, originalFilePath):
    originalPath = Path(originalFilePath)
    outputFilename = "{0}_{1}".format(fileBlob.id, originalPath.name)
    outputPath = TEMP_FOLDER_PATH / outputFilename

    outputPath.write_bytes(fileBlob.read_raw())
    return str(outputPath)


def isFormattableJSSourceFile(pathString):
    filePath = Path(pathString)

    if(filePath.suffix in (".js", ".jsx")):
        parentsSet = set(filePath.parents)
        matchingFolders = JS_SOURCE_PATHS & parentsSet
        isSourceFile = any(matchingFolders)

        if isSourceFile:
            isActuallyALib = any([filePath.match("*{0}*".format(ignoreName)) for ignoreName in JS_LIBS_TO_IGNORE])
            return not isActuallyALib

    return False


def isFormattablePythonSourceFile(pathString):
    filePath = Path(pathString)

    shouldFormat = False

    if(filePath.suffix == ".py"):
        moduleFolder = filePath.parts[0]

		# All our services have almost all their source files in the root folder
        if(moduleFolder in PYTHON_SERVICES):
            if(len(filePath.parts) == 2):
                # File is at the top level of the module
                shouldFormat = filePath.name not in PYTHON_FILES_TO_IGNORE
            else:
                moduleSourceFolders = PYTHON_SOURCE_SUBFOLDERS.get(moduleFolder, [])
                # Some services have actual code that's nested one level deep
                shouldFormat = filePath.parts[1] in moduleSourceFolders

    return shouldFormat


# Create a list of all file paths and entries in this Git tree
def walktree(repo, tree, results = [], path=[]):
    for e in tree:
        results.append(("/".join(path + [e.name]), e))
        if e.type == "tree":
            walktree(repo, repo[e.id], results, path + [e.name])
    return results


def ddhhmmss(seconds):
    """Convert seconds to a time string "[[[DD:]HH:]MM:]SS".
    """
    dhms = ''
    for scale in 86400, 3600, 60:
        result, seconds = divmod(seconds, scale)
        if dhms != '' or result > 0:
            dhms += '{0:02d}:'.format(result)
    dhms += '{0:02d}'.format(seconds)
    return dhms

def update(obj, newValues):
    newObj = obj.copy()
    newObj.update(newValues)
    return newObj

def replaceEntry(array, old, new):
    if old not in array:
        return array
    index = array.index(old)
    newArray = array.copy()
    newArray[index] = new
    return newArray

def normalizeEntry(fileEntry):
    newText = normalize("NFKD", str(fileEntry["source"], 'utf-8', 'ignore'))
    return update(fileEntry, {"source": newText})