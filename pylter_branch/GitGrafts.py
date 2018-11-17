# -*- coding: utf-8 -*-
"""
Grafts support over pygit2
"""

from pygit2 import Repository, Commit, Oid
import os.path


def _ishexdigit(char):
    return char in '0123456789abcdefABCDEF'


def _isSHA1(candidate):
    return len(candidate) == 40 and all(map(_ishexdigit, candidate))


class GitGrafts:
    def __init__(self, repository: Repository):
        assert (isinstance(repository, Repository))
        self._repository = repository
        self.grafts = {}

        grafts_path = repository.path
        if not repository.is_bare:
            grafts_path = os.path.join(grafts_path, '.git')
        grafts_path = os.path.join(grafts_path, 'info', 'grafts')
        self._load_grafts(grafts_path)

    def __iter__(self):
        return iter(self.grafts)

    def __len__(self):
        return len(self.grafts)

    def __getitem__(self, item):
        """
        [] lookups commit parents. If commit is grafted, substitution commits are returned
        if commit is not grafted, falls back to repository lookup
        :param item: SHA1 of commit to look up
        :return: tuple of commit parents SHA1
        """
        if not isinstance(item, Oid):
            item = Oid(hex=item)

        try:
            return self.grafts[item]
        except KeyError:
            commit = self._repository[item]
            assert(isinstance(commit, Commit))
            return tuple( parent for parent in commit.parent_ids )

    def _load_grafts(self, grafts_path: str):
        if not os.path.exists(grafts_path):
            return

        # TODO: decide whether file unavailablity should be treated as correct behaviour
        with open(grafts_path, 'r') as grafts_file:
            for line in grafts_file:
                self._process_line(line)

    def _process_line(self, line: str):
        line.strip(' ')
        if line.startswith('#'):
            return

        ids = line.split()
        for entry in ids:
            assert(_isSHA1(entry))

        self.grafts[Oid(hex = ids[0])] = tuple(Oid(hex = entry) for entry in ids[1:])
