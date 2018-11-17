from unicodedata import normalize

from black import format_str, InvalidInput
from repoFilterUtils import update, normalizeEntry



def formatSource(sourceText):
    formattedSource = sourceText
    try:
        formattedSource = format_str(sourceText, 120)
    except Exception as e:
        print(e)
    return formattedSource

def formatFileEntry(fileEntry):
    normalizedEntry = normalizeEntry(fileEntry)
    formattedSource = formatSource(normalizedEntry["source"])
    return update(fileEntry, {"source" : formattedSource})

def formatPYFiles(filesList):
    formattedFiles = list(map(formatFileEntry, filesList))
    return formattedFiles