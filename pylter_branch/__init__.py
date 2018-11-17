# -*- coding: utf-8 -*-


import re
import pygit2

from . import GitGrafts
from . import GitReplaces
from . import TopoSort
from . import TreeProcessor


class RepositoryProcessor:
    sha1regex = re.compile('([0-9a-fA-F]{8,40})')

    def __init__(self, repository: pygit2.Repository, replaced_commits=None, known_objects=None):
        self._repository = repository
        self._grafts = GitGrafts.GitGrafts(self._repository)
        self._replaces = GitReplaces.GitReplaces(self._repository)
        self.replaced_commits = {} if replaced_commits is None else replaced_commits
        self._known_objects = set() if known_objects is None else known_objects

    def process(self):
        # Loading
        sorter = TopoSort.TopoSort()
        self.on_begin_load()
        for object_key in self._repository:
            if object_key in self._known_objects:
                continue

            self._known_objects.add(object_key)

            try:
                obj = self._repository[object_key]
            except MemoryError:
                self.on_memory_error(object_key)
                continue

            if obj.type == pygit2.GIT_OBJ_COMMIT:
                commit = obj.peel(pygit2.Commit)
                self._read_commit(commit, sorter)
                self.on_commit_loaded(object_key)

        self.on_end_load()
        queue = sorter.sort()
        queue.reverse()
        # Processing
        self.on_begin_processing()
        for commit_id in queue:
            self._process_commit(commit_id)

        self.on_end_processing()

        # Rewriting refs
        for ref_name in self._repository.references:
            ref = self._repository.references[ref_name]
            if ref.type == pygit2.GIT_REF_SYMBOLIC:
                continue

            target = self._repository[ref.target]
            if isinstance(target, pygit2.Tag):
                commit_id = self.replaced_commits[target.target]
                ref.delete()
                tag_id = self._repository.create_tag(target.name, commit_id, target.get_object().type, target.tagger,
                                                     target.message)
            else:
                ref.set_target(self.replaced_commits[ref.target])

    def _read_commit(self, commit: pygit2.Commit, sorter: TopoSort.TopoSort):
        # fill parents. Possibly grafted and respecting refs/replace
        commit_id = commit.oid
        parents = [parent for parent in self._grafts[commit.oid]]
        parents.extend([parent for parent in commit.parent_ids])

        for parent in parents:
            sorter.add_edge(commit_id, parent)
            sorter.add_edge(commit_id, self._replaces[parent])

        # obtain possible dependencies from commit message
        # message = commit.message
        # match = self.sha1regex.search(message)
        # while match:
        #     sha1_candidate = match.group().lower()
        #     object_candidate = self._repository.git_object_lookup_prefix(sha1_candidate)
        #     if object_candidate and object_candidate.type == pygit2.GIT_OBJ_COMMIT:
        #         sorter.add_edge(commit_id, self._replaces[object_candidate.oid])
        #     match = self.sha1regex.search(message, match.end())

        sorter.add_vertex(commit_id)

    def _process_commit(self, commit_id: pygit2.Oid):
        if commit_id in self.replaced_commits:
            return

        commit = self._repository[commit_id]

        assert (commit.type == pygit2.GIT_OBJ_COMMIT)

        for parent_id in self._grafts[commit_id]:
            assert parent_id in self.replaced_commits

        original_parents = tuple(self._replaces[parent] for parent in self._grafts[commit_id])
        parents = []

        for parent in original_parents:
            try:
                parent = self.replaced_commits[parent]
            except KeyError:
                pass

            if isinstance(parent, pygit2.Oid):
                if parent not in parents:
                    parents.append(parent)
            else:
                for single_parent in parent:
                    if single_parent not in parents:
                        parents.append(single_parent)

        tree = self._build_commit_tree(commit.tree)
        message = self.filter_message(commit.message)
        author = self.filter_author(commit.author)
        committer = self.filter_committer(commit.committer)

        new_commit = self.filter_commit(commit_id, author, committer, message, tree, parents)
        self.replaced_commits[commit_id] = new_commit
        if (isinstance(new_commit, pygit2.Oid)):
            self.replaced_commits[new_commit] = new_commit
        self._known_objects.add(new_commit)

    def _build_commit_tree(self, original_tree: pygit2.Tree):
        tree = TreeProcessor.TreeWrapper(self._repository, original_tree)
        tree = self.filter_tree(tree)
        return tree.hex()

    @staticmethod
    def _filter_identity(identity):
        if identity.name:
            return identity
        if '@' in identity.email:
            auto_name = identity.email[:identity.email.find('@')]
            return pygit2.Signature(name=auto_name, email=identity.email, time=identity.time,
                                    offset=identity.offset)
        return identity

    def filter_tree(self, tree: TreeProcessor.TreeWrapper):
        return tree

    def filter_message(self, message):
        return message

    def filter_author(self, author):
        return self._filter_identity(author)

    def filter_committer(self, committer):
        return self._filter_identity(committer)

    @staticmethod
    def skip_commit(commit_id, author, committer, message, tree, parents):
        if len(parents) == 1:
            return parents[0]
        else:
            return parents.copy()

    def filter_commit(self, commit_id, author, committer, message, tree, parents):
        return self._repository.create_commit(None, author, committer, message, tree, parents)

    def on_memory_error(self, sha1):
        pass

    def on_begin_load(self):
        pass

    def on_end_load(self):
        pass

    def on_commit_loaded(self, sha1):
        pass

    def on_begin_processing(self):
        pass

    def on_end_processing(self):
        pass
