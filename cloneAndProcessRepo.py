from pathlib import Path
import shutil, tempfile
import time, datetime as dt

import pygit2
from pygit2 import IndexEntry

from pylter_branch import RepositoryProcessor, TreeProcessor

from repoFilterUtils import *

from transformJSFiles import rewriteAvailableJSFiles
from transformPYFiles import formatPYFiles


GIT_DIFF_FIND_ALL = 0x0ff

def createFileEntry(repo, diffEntry):
    nf = diffEntry.new_file
    fileBlob = repo[nf.id]

    return {
        "name" : nf.path,
        "mode" : nf.mode,
        "hash" : str(nf.id),
        "source" : fileBlob.read_raw()
    }

def createTransformedEntry(fileEntry):
    return (fileEntry["name"], fileEntry["mode"], fileEntry["source"])


class MyRepoProcessor(RepositoryProcessor):
    def __init__(self, repository: pygit2.Repository, firstBadCommit = None):
        super().__init__(repository)

        self.currentCommitNumber = 0
        self.totalCommits = 0
        self.allCommitIds = set()

        self.seenFirstBadCommit = False
        self.firstBadCommit = firstBadCommit


    def on_commit_loaded(self, sha1):
        self.allCommitIds.add(sha1)

    def on_begin_load(self):
        print("Loading existing commits...")

    def on_end_load(self):
        self.totalCommits = len(self.allCommitIds)
        print("Loaded {0} commits".format(self.totalCommits))

    def on_begin_processing(self):
        print("Processing commits...".format(self.totalCommits))
        self.startTime = time.time()

    def calculateProgressTimes(self):
        endTime = time.time()
        elapsedTime = endTime - self.startTime

        secondsPerCommit = elapsedTime / self.currentCommitNumber
        commitsRemaining = self.totalCommits - self.currentCommitNumber
        numSecondsRemaining = commitsRemaining * secondsPerCommit

        elapsedString = ddhhmmss(int(elapsedTime))
        etaString = ddhhmmss(int(numSecondsRemaining)) if numSecondsRemaining >= 60 else "{0: >#0.3f}s".format(numSecondsRemaining)

        return (secondsPerCommit, elapsedString, etaString)


    def on_end_processing(self):
        secondsPerCommit, elapsedString, etaString = self.calculateProgressTimes()

        print("\nCommit processing complete. Total time: {0} ({1: >#0.3f}s/commit)".format(elapsedString, secondsPerCommit))
        print("Rewriting refs...")

    def printCommitProgressMessage(self, commit):
        firstMessageLine = commit.message.splitlines()[0]
        authorName = commit.author.name
        dateString = dt.datetime.utcfromtimestamp(commit.commit_time).strftime("%Y-%m-%d")

        secondsPerCommit, elapsedString, etaString = self.calculateProgressTimes()

        print("Processing commit {0} ({1}/{2} - {3} elapsed, {4} remaining, {5: >#0.3f}s/commit)".format(
            commit.id, self.currentCommitNumber, self.totalCommits, elapsedString, etaString, secondsPerCommit)
        )
        print("{0} ({1}): {2}".format(dateString, authorName, firstMessageLine))

    def filter_commit(self, commit_id, author, committer, message, tree, parents):
        self.currentCommitNumber += 1
        currentCommit = self._repository[commit_id]
        self.printCommitProgressMessage(currentCommit)

        rewrittenCommitId = self.rewriteCommit(currentCommit, author, committer, message, tree, parents)

        print("Rewrote {0} to {1}\n".format(currentCommit.id, rewrittenCommitId))

        return rewrittenCommitId

    def rewriteCommit(self, currentCommit, author, committer, message, tree, parents):
        destRepo = self._repository

        shouldSkipCommit = False

        if self.firstBadCommit and not self.seenFirstBadCommit:
            self.seenFirstBadCommit = currentCommit.id.hex.startswith(self.firstBadCommit)
            shouldSkipCommit = not self.seenFirstBadCommit

        if not parents or shouldSkipCommit:
            return destRepo.create_commit(None, author, committer, message, tree, parents)
        else:

            index = destRepo.index

            # Look up the original parent commit
            parentCommit = currentCommit.parents[0]

            # The base class already looked up rewritten commit IDs
            rewrittenParentHash = parents[0]

            # Look up that commit object too
            rewrittenParentCommit = destRepo[rewrittenParentHash]

            # Reset the index to the previously-rewritten commit as our starting point
            index.read_tree(rewrittenParentCommit.tree)

            # Calculate the original diff for this commit
            diff = destRepo.diff(parentCommit, currentCommit)

            diffOptions = pygit2.GIT_DIFF_FIND_RENAMES | pygit2.GIT_DIFF_FIND_AND_BREAK_REWRITES

            diff.find_similar(GIT_DIFF_FIND_ALL, rename_threshold=85)

            print("Checking deltas...")
            filteredFiles = self.filterChangedFiles(diff)

            newTreeId = self.transformChangedFiles(currentCommit, *filteredFiles)

            return destRepo.create_commit(None, author, committer, message, newTreeId, parents)


    def filterChangedFiles(self, diff):
        changedJSFiles = []
        changedPYFiles = []
        allOtherFiles = []

        for delta in diff.deltas:
            statusChar = delta.status_char()
            # Check for any modified or added files
            if statusChar in ('M', 'A', 'R', 'C'):
                if statusChar == 'R':
                    self.removeFileFromIndex(delta.old_file.path)

                if (isFormattableJSSourceFile(delta.new_file.path)):
                    changedJSFiles.append(delta)
                elif (isFormattablePythonSourceFile(delta.new_file.path)):
                    changedPYFiles.append(delta)
                else:
                    allOtherFiles.append(delta)
            elif statusChar == 'D':
                self.removeFileFromIndex(delta.old_file.path)
            else:
                q = 42
                raise Exception("Unexpected delta status type!")

        return (changedJSFiles, changedPYFiles, allOtherFiles)



    def transformChangedFiles(self, currentCommit, changedJSFiles, changedPYFiles, allOtherFiles):
        transformedFiles = []

        destRepo = self._repository
        index = destRepo.index

        if changedJSFiles or changedPYFiles:
            print("Transforming JS+PY files...")

            for delta in changedJSFiles + changedPYFiles:
                new_file = delta.new_file
                # Remove the existing entry, if any:
                try:
                    index.remove(new_file.path)
                except:
                    pass

            for delta in changedJSFiles:
                print("JS: " + delta.new_file.path)

            for delta in changedPYFiles:
                print("PY: " + delta.new_file.path)

            currentCommitId = str(currentCommit.id)
            transformedJSFiles = self.transformJSFiles(currentCommitId, changedJSFiles)
            transformedFiles.extend(transformedJSFiles)

            transformedPYFiles = self.transformPYFiles(changedPYFiles)
            transformedFiles.extend(transformedPYFiles)

            for originalFilePath, originalFileMode, transformedFileContents in transformedFiles:
                newBlobId = destRepo.create_blob(transformedFileContents)
                fileBlob = destRepo[newBlobId]

                self.addFileToIndex((originalFilePath, originalFileMode), fileBlob=fileBlob)#externalPath=transformedFilePath)

        for delta in allOtherFiles:
            # Replicate all other file operations
            nf = delta.new_file
            fileBlob = destRepo[nf.id]
            self.addFileToIndex((nf.path, nf.mode), fileBlob=fileBlob)

        newTreeId = index.write_tree()
        return newTreeId

    def transformJSFiles(self, currentCommitId, changedJSFiles):
        if not changedJSFiles:
            return []

        destRepo = self._repository
        jsFileEntries = [createFileEntry(destRepo, diffEntry) for diffEntry in changedJSFiles]
        rewrittenFileEntries = rewriteAvailableJSFiles(currentCommitId, jsFileEntries)
        transformationEntries = list(map(createTransformedEntry, rewrittenFileEntries))

        return transformationEntries

    def transformPYFiles(self, changedPYFiles):
        if not changedPYFiles:
            return []

        destRepo = self._repository
        pyFileEntries = [createFileEntry(destRepo, diffEntry) for diffEntry in changedPYFiles]
        rewrittenFileEntries = formatPYFiles(pyFileEntries)
        transformationEntries = list(map(createTransformedEntry, rewrittenFileEntries))

        return transformationEntries

    def addFileToIndex(self, fileAttributes, fileBlob=None, externalPath=None, ):
        destRepo = self._repository
        index = destRepo.index

        filePath, fileMode = fileAttributes

        newBlobId = None

        if(fileBlob):
            if fileBlob.id not in destRepo:
                destRepo.write(fileBlob.type, fileBlob.read_raw())
            newBlobId = fileBlob.id
        elif(externalPath):
            newBlobId = destRepo.create_blob_fromdisk(externalPath)

        if not newBlobId:
            raise Exception("Could not add file: attributes: {0}, blob = {1}, externalPath = {2}".format(fileAttributes, fileBlob, externalPath))

        indexEntry = IndexEntry(filePath, newBlobId, fileMode)
        index.add(indexEntry)

        return newBlobId

    def removeFileFromIndex(self, filePath):
        try:
            destRepo = self._repository
            index = destRepo.index
            index.remove(filePath)
            q = 42
        except Exception as e:
            z = 42
            pass


def main(sourcePath = SOURCE_REPO_PATH, destPath = OUTPUT_REPO_PATH):
    strSourcePath = str(sourcePath)
    strDestPath = str(destPath)

    print("Deleting existing repo...")
    if destPath.exists():
        shutil.rmtree(strDestPath)

    print("Cloning repo at {0} to {1}".format(strSourcePath, strDestPath))
    destRepo = pygit2.clone_repository(strSourcePath, strDestPath, True)

    repoProcessor = MyRepoProcessor(destRepo, firstBadCommit=None)
    repoProcessor.process()

    print("\nDone")

if __name__ == "__main__":
    main()