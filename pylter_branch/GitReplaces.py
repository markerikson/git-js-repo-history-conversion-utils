# -*- coding: utf-8 -*-

from pygit2 import Repository, Oid


class GitReplaces:
    def __init__(self, repository: Repository):
        assert (isinstance(repository, Repository))
        self._repository = repository
        self._replaces = {}
        self._read_replaces()

    def _read_replaces(self):
        prefix = 'refs/replace/'
        prefix_len = len(prefix)

        for ref in self._repository.references:
            if ref.startswith(prefix):
                self._replaces[ Oid(hex=ref[prefix_len:]) ] = self._repository.references[ref].target

    def __getitem__(self, item):
        if not isinstance(item, Oid):
            item = Oid(hex=item)

        try:
            return self._replaces[item]
        except KeyError:
            return item

    def __iter__(self):
        return iter(self._replaces)

    def __len__(self):
        return len(self._replaces)
