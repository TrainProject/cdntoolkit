# coding=utf-8

import collections
import json
import os
import shutil
import subprocess
import time
import traceback

try:
    import git
except ImportError:
    git = None
    _ = git


class Error(RuntimeError):
    code = 444

    def __str__(self):
        return json.dumps(dict(code=self.code, reason=str(self)))


class ParamsError(Error):
    code = 450


class UnsupportedSchemeError(ParamsError):
    code = 451


class MissingRepositoryURL(ParamsError):
    code = 452


class CommitError(Error):
    code = 453


class DiffError(Error):
    code = 454


class CheckoutError(Error):
    code = 455


class PullError(Error):
    code = 456


class UpdateError(Error):
    code = 457


class NginxTestError(Error):
    code = 458


class NginxReloadError(Error):
    code = 459


class exception:
    def __init__(self, error) -> None:
        self.error = error

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Error as e:
                raise e
            except Exception:
                raise self.error(traceback.format_exc())

        return wrapped_f


class C3:
    @exception(ParamsError)
    def __init__(self, repo, git_dir='', working_tree='', username='', password='') -> None:
        """creates a C3 object, the parameter repo is either a local directory or a remote HTTP URL."""
        url = None
        if os.path.isdir(repo):
            git_dir = repo
        else:
            from urllib.parse import urlparse, urlunparse
            url = repo
            u = urlparse(url)
            if u.scheme != 'http':
                raise UnsupportedSchemeError('only supports http yet')

            if username and password:
                l = list(u)
                l[1] = '{username}:{password}@{hostname}'.format(username=username,
                                                                 password=password,
                                                                 hostname=u.hostname)
                if u.port:
                    l[1] += ':{port}'.format(port=u.port)
                url = urlunparse(l)

            if not git_dir:
                # reuses the basename from URL path
                git_dir = os.path.basename(u.path)

        if git_dir:
            git_dir = os.path.abspath(os.path.realpath(git_dir))
        if working_tree:
            working_tree = os.path.abspath(os.path.realpath(working_tree))

        try:
            self.git_dir = git_dir
            self.working_tree = working_tree or git_dir
            self.repo = git.Repo(git_dir)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            if not url:
                raise MissingRepositoryURL('Repository URL is required')

            print('No valid repository({dir}) found on local machine, cloning from remote {url}'.format(
                dir=git_dir, url=url
            ))

            dst = None
            if git_dir not in ('.', '..') and os.path.isdir(git_dir):
                # remains existed file
                dst = git_dir + '_' + str(time.time())
                os.rename(git_dir, dst)

            try:
                self.repo = git.Repo.clone_from(url, git_dir, bare=working_tree != git_dir)
                try:
                    self.repo.remote()
                except ValueError:
                    self.repo.create_remote('origin', url)
            except Exception as e:
                shutil.rmtree(git_dir, ignore_errors=True)
                if dst:
                    # restores
                    os.rename(dst, git_dir)
                raise e

        # always make the working tree
        try:
            os.makedirs(self.working_tree, exist_ok=True)
        except TypeError as e:
            if str(e).find('exist_ok') != -1:
                try:
                    os.makedirs(self.working_tree)
                except Exception as e:
                    if str(e).find('File exists') == -1:
                        raise e
            else:
                raise e

        # set the git-shell CWD
        self.repo.git._working_dir = self.working_tree
        # always run with git-dir and work-tree
        self.repo.git.set_persistent_git_options(git_dir=self.git_dir, work_tree=self.working_tree)

    @exception(CommitError)
    def commit(self):
        """Commit returns the most recent commit"""
        try:
            return str(self.repo.commit())
        except Exception as e:
            if str(e).find("Reference at 'refs/heads/master' does not exist") != -1:
                pass
            else:
                raise e

    @exception(CommitError)
    def all_commits(self):
        """All_commits returns a list of commit from the newest to the oldest"""
        try:
            return [str(c) for c in self.repo.iter_commits()]
        except Exception as e:
            if str(e).find("Reference at 'refs/heads/master' does not exist") != -1:
                return []
            else:
                raise e

    @exception(DiffError)
    def diff(self):
        """Diff checks if local files are modified."""
        dirty = self.repo.is_dirty()
        if not dirty and self.repo.bare:
            dirty = len(self.repo.git.diff()) > 0

        return dirty or self.repo.head.is_detached

    @exception(CheckoutError)
    def checkout(self, commit=None):
        """Checkout resets local repository into the specific commit.
        If no commit specified, just discards any modifications."""

        # C3 doesn't provide interface to switch branch, so only needs to check master branch
        if self.repo.head.is_detached:
            self.repo.heads.master.checkout()

        if not commit or commit == self.commit():
            self.repo.head.reset(index=True, working_tree=True)
        else:
            self.repo.head.reset(commit=commit, index=True, working_tree=True)

    @exception(PullError)
    def pull(self, commit=None):
        """Pull retrieves specific commit from upstream.
        If no commit specified, it pulls the latest version."""
        needs_fetch = True
        if commit:
            # always iterate each commit for safety
            for c in self.all_commits():
                if c == commit:
                    needs_fetch = False
                    break

        if needs_fetch:
            self.repo.git.pull('origin', 'master')
            if commit not in self.all_commits():
                raise RuntimeError

        self.checkout(commit)

    @exception(UpdateError)
    def update(self, commit=None, action=None):
        """Update updates into the specific commit from upstream.
        If no commit specified, uses the latest version."""
        present = self.commit()
        try:
            self.pull(commit)
            if action:
                action()
        except Exception as e:
            if present:
                self.checkout(present)
            raise e


Target = collections.namedtuple('Target', ['repo', 'commit', 'git_dir', 'working_tree', 'username', 'password'])


@exception(NginxTestError)
def nginx_test():
    subprocess.call(['/usr/local/nginx/sbin/nginx', '-c', '/usr/local/nginx/conf/nginx.conf', '-t'])


@exception(NginxReloadError)
def nginx_reload():
    subprocess.call(['/usr/local/nginx/sbin/nginx', '-c', '/usr/local/nginx/conf/nginx.conf', '-s', 'reload'])


def snapshot(targets):
    """ [Target] -> [Target] -- replace commit field by current version for each of input target """
    results = []
    for target in targets:
        c3 = C3(target.repo,
                git_dir=target.git_dir,
                working_tree=target.working_tree,
                username=target.username,
                password=target.password)

        results.append(target._replace(commit=c3.commit()))

    return results


def update(targets, action=nginx_test):
    """ [Target] -> [{last_commit, commit, exception}] """
    results = []

    for target in targets:
        last_commit = None
        try:
            c3 = C3(target.repo,
                    git_dir=target.git_dir,
                    working_tree=target.working_tree,
                    username=target.username,
                    password=target.password)
            last_commit = c3.commit()
            c3.update(target.commit, action)
            results.append(dict(last_commit=last_commit, commit=c3.commit()))
        except Exception as e:
            r = dict(exception=e)
            if last_commit:
                r['commit'] = last_commit
            results.append(r)

    return results


def diff(targets):
    """ [Target] -> [{diff, exception}] """
    results = []

    for target in targets:
        try:
            c3 = C3(target.repo,
                    git_dir=target.git_dir,
                    working_tree=target.working_tree,
                    username=target.username,
                    password=target.password)
            results.append(dict(diff=c3.diff()))
        except Exception as e:
            results.append(dict(exception=e))

    return results


def checkout(targets):
    """ [Target] -> [{last_commit, diff, commit, exception}] """
    results = []

    for target in targets:
        last_commit, diff = None, None
        try:
            c3 = C3(target.repo,
                    git_dir=target.git_dir,
                    working_tree=target.working_tree,
                    username=target.username,
                    password=target.password)
            last_commit = c3.commit()
            diff = c3.diff()
            c3.checkout(target.commit)
            results.append(dict(last_commit=last_commit, diff=diff, commit=c3.commit()))
        except Exception as e:
            r = dict(exception=e)
            if last_commit is not None:
                r['commit'] = last_commit
            if diff is not None:
                r['diff'] = diff
            results.append(r)

    return results


def main():
    def pip_install(name, module=None):
        import pip
        import sys

        def check_module(name):
            import pkgutil
            loader = pkgutil.find_loader(name)
            return loader is not None

        if not check_module(name):
            pip_target = sys.exec_prefix + '/lib/python{ver}/site-packages'.format(ver=sys.version[:3])
            pip.main(['install', '-U', '-t', pip_target, module or name])

    pip_install('git', 'GitPython')
    pip_install('fire')

    try:
        import fire
        fire.Fire()
    except ImportError:
        fire = None
        _ = fire


if __name__ == '__main__':
    main()
