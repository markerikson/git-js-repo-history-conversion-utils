# -*- coding: utf-8 -*-

import pygit2

PATH_SEPARATOR = '/'


class TreeWrapper:
    @classmethod
    def is_tree(cls, entry):
        if isinstance(entry, cls):
            return True
        if hasattr(entry, 'type'):
            return entry.type == 'tree'
        return False

    @classmethod
    def is_git_tree(_, entry):
        return hasattr(entry, 'type') and entry.type == 'tree'

    def __init__(self, repository: pygit2.Repository, tree: pygit2.Tree):
        self._repository = repository
        self._tree = tree
        self._raw_data = {}

    def __contains__(self, item):
        return (self._tree and (item in self._tree)) or (item in self._raw_data)

    def __getitem__(self, item):
        if self._tree:
            return self._wrap_git_entry(self._tree[item])
        else:
            return self._raw_data[item]

    def _wrap_git_entry(self, entry):
        if TreeWrapper.is_git_tree(entry):
            try:
                return TreeWrapper(self._repository, self._repository[entry.id])
            except pygit2.GitError:
                return entry
        else:
            return entry

    def _unfold(self):
        if self._tree is None:
            return

        assert (not self._raw_data)
        for entry in self._tree:
            self._raw_data[entry.name] = self._wrap_git_entry(entry)

        self._tree = None

    def _insert(self, name, entry):
        self._unfold()
        if TreeWrapper.is_git_tree(entry):
            entry = self._wrap_git_entry(entry)
        self._raw_data[name] = entry

    def _rm(self, name):
        if name in self:
            self._unfold()
            del self._raw_data[name]
            return True
        return False

    def _get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def _merge_tree(self, rhs):
        assert isinstance(rhs, TreeWrapper)
        self._unfold()
        rhs._unfold()
        for name, entry in rhs._raw_data.items():
            if name in self:
                own = self._raw_data[name]
                if own == entry:
                    continue
                elif isinstance(own, TreeWrapper) and isinstance(entry, TreeWrapper):
                    own._merge_tree(entry)
                else:
                    print('File', name, ' exists in source and destination.')
                    pass
                    #raise RuntimeError("Tree was expected")
            else:
                self._insert(name, entry)

    def is_dirty(self):
        return bool(self._raw_data) and self._tree is None

    def is_empty(self):
        return len(self._raw_data) == 0 and self._tree is None

    def hex(self):
        if self._tree is None:
            self.save()
        if self._tree is not None:
            return self._tree.hex
        else:
            return '0'*40

    def save(self):
        if self._tree:
            return

        builder = self._repository.TreeBuilder()
        for name, entry in self._raw_data.items():
            if isinstance(entry, TreeWrapper):
                builder.insert(name, entry.hex(), pygit2.GIT_FILEMODE_TREE)
            else:
                builder.insert(name, entry.hex, entry.filemode)

        self._tree = self._repository[builder.write()]
        self._raw_data = {}

    def get(self, path, default=None):
        path_parts = path.split(PATH_SEPARATOR, 1)
        if len(path_parts) == 1:
            return self._get(path, default)

        immediate, rest = path_parts
        child = self._get(immediate)
        if child is None:
            return default
        if not isinstance(child, TreeWrapper):
            raise RuntimeError("Could not get tree")

        return child.get(rest, default)

    def rm(self, path: str):
        path_parts = path.split(PATH_SEPARATOR, 1)
        if len(path_parts) == 1:
            return self._rm(path)

        immediate, rest = path_parts
        child = self._get(immediate)

        if child is None:
            return False
        if not isinstance(child, TreeWrapper):
            raise RuntimeError("Could not get tree")

        if child.rm(rest):
            if child.is_empty():
                return self._rm(immediate)
            else:
                # force unfolding
                self._insert(immediate, child)
            return True

        return False

    def insert(self, path: str, entry):
        path_parts = path.split(PATH_SEPARATOR, 1)
        if len(path_parts) == 1:
            self._insert(path, entry)
            return

        immediate, rest = path_parts
        child = self._get(immediate, TreeWrapper(self._repository, None))
        if not isinstance(child, TreeWrapper):
            raise RuntimeError("Tree expected. Something else found")
        child.insert(rest, entry)
        self._insert(immediate, child)

    def mv(self, old_path: str, new_path: str):
        node = self.get(old_path)
        if node is None:
            return

        placeholder = self.get(new_path)
        if placeholder is None:
            self.insert(new_path, node)
        elif isinstance(node, TreeWrapper) and isinstance(placeholder, TreeWrapper):
            placeholder._merge_tree(node)
            self.insert(new_path, placeholder)
        elif not TreeWrapper.is_tree(node) and not TreeWrapper.is_tree(placeholder):
            self.insert(new_path, node)
        else:
            raise RuntimeError("Incompatible types at source and destination")
        self.rm(old_path)
