from __future__ import print_function

import os
from shlex import split as shlex_split
import subprocess
import time

import helpers


__git_dir = (os.path.abspath(os.path.dirname(__file__)))
try:
    isinstance('h', unicode)
    spkwargs = dict()
except Exception:
    spkwargs = {'encoding': 'utf8'}


class GITException(Exception):
    pass



class GITSubprocessException(subprocess.CalledProcessError):
    def __init__(self, exc, cwd):
        super(GITSubprocessException, self).__init__(exc.returncode, exc.cmd, exc.output)

        self.cwd = cwd


    def __str__(self):
        return """{} when ran from directory '{}'
Command output: {}""".format(super(GITSubprocessException, self).__str__(), self.cwd, self.output)



class GIT(object):
    REMOTE_PREFIX = "remote:"
    REMOTE_PREFIX_LEN = len(REMOTE_PREFIX)
    MASTER = "master"


    def __init__(self, path):
        super(GIT, self).__init__()

        self._default_branch = None
        self._path = os.path.abspath(path)
        self._branch = None
        self._url = None


    def path(self):
        return self._path


    def url(self):
        return self._url


    @staticmethod
    def get_config(cfg, path = "."):
        """
        Returns the value of the configuration item 'cfg'
        """
        try:
            return subprocess.check_output(shlex_split("git config {}".format(cfg)), stderr = subprocess.STDOUT, cwd = path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            if not e.output:
                return ""
            raise GITSubprocessException(e, path)


    @staticmethod
    def check_minimal_config(path = "."):
        user_email = GIT.get_config("user.email", path)
        user_name = GIT.get_config("user.name", path)
        if not user_name:
            # os.getlogin() does not handle su
            # but pwd is not available on Windows
            try:
                import pwd
                user_name = pwd.getpwuid(os.getuid()).pw_name
            except ImportError:
                user_name = os.getlogin()

        if user_email:
            user_email = ""
        else:
            user_email = """
E-mail address is not set in git. Please set it with:

git config --global user.email my-email@ess.eu
"""

        if user_name == "vagrant":
            user_name = """
Username is not set in git. Please set it with:

git config --global user.name "My Name"
"""
        else:
            user_name = ""

        if user_email or user_name:
            raise GITException(user_name + user_email)


    @staticmethod
    def __is_repo(path):
        """
        Returns True if 'path' is inside a work tree of a git repository
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --is-inside-work-tree"), stderr = subprocess.STDOUT, cwd = path, **spkwargs).strip().lower() == "true"
        except subprocess.CalledProcessError as e:
            if e.output.strip().lower().startswith("fatal: not a git repository"):
                return False

            raise GITSubprocessException(e, path)


    @staticmethod
    def clone(url, path = '.', branch = None, update = False, initialize_if_empty = False, verbose = True, gitignore_contents = "", initializer = None):
        """
        Clone the repository at 'url' into 'path' and possibly checkout 'branch'

        If repository is already cloned, checkout 'branch'

        If 'update' is True then the master branch will be updated
        """
        # FIXME: I've deleted and recreated the repo but an old working copy was still in the output folder and git.fetch choked on it
        url = helpers.sanitize_url(url)
        git = GIT(path)
        # Append '.git' if needed
        url = git.__set_url(url)
        path = os.path.abspath(path)
        if not git.is_repo():
            # If 'path' is not a repository then clone url
            git.__clone(url, branch, initialize_if_empty = initialize_if_empty, verbose = verbose, gitignore_contents = gitignore_contents, initializer = initializer)
            return git

        if not os.path.samefile(git.get_toplevel_dir(), path):
            # This is some other repository working tree, we can clone a new one here
            git.__clone(url, branch, initialize_if_empty = initialize_if_empty, verbose = verbose, gitignore_contents = gitignore_contents, initializer = initializer)
            return git

        # Have to check if this repository is the one we need
        if helpers.sanitize_url(helpers.url_strip_user(git.get_origin())) != helpers.url_strip_user(url):
            raise GITException("Found unrelated git repository in {} (belongs to {}), refusing to overwrite".format(path, git.get_origin()))

        git._default_branch = git.get_default_branch()

        if initialize_if_empty:
            git.__initialize_if_empty(branch, gitignore_contents, initializer, verbose = verbose)

        # Return if empty
        if not git.get_branches():
            if branch is not None:
                raise GITException("Empty repository does not have branch '{}'".format(branch))
            git._branch = git._default_branch
            return git

        if update:
            # FIXME: If push of initialization failed, then there is no remote master

            if update is True:
                # Do a 'full' update; all branches and tags
                try:
                    git.pull()
                except GITException as e:
                    if e.message != "Deleted remote ref":
                        raise
                    # The remote branch was deleted, let's switch to the default one and try again...
                    git.checkout(git._default_branch)
                    git.pull()
            else:
                # 'Lazy' update; only update the default branch
                if git.get_current_branch() == git._default_branch:
                    git.pull(git._default_branch)
                else:
                    # Not on master, so fetch master and also fetch remote tags to fail early if trying to use an already existing tag
                    git.fetch(git._default_branch, git._default_branch)
                    git.fetch_tags()

        # Check if we need to checkout 'branch'
        if branch:
            git.checkout(branch)
        else:
            # Update the current branch
            git._branch = git.get_current_branch()

        return git


    def set_config(self, cfg, value):
        """
        Sets local configuration item 'cfg' to 'value'
        """
        try:
            return subprocess.check_output(shlex_split("git config {} {}".format(cfg, value)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            if not e.output:
                return ""

            raise GITSubprocessException(e, self._path)


    def get_toplevel_dir(self):
        """
        Returns the toplevel directory of the repository
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --show-toplevel"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def get_origin(self):
        """
        Returns the remote url of 'origin'
        """
        try:
            return subprocess.check_output(shlex_split("git ls-remote --get-url origin"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def get_default_branch(self):
        """
        Returns the name of the remote branch associated with remote HEAD
        """

        if self._default_branch is not None:
            return self._default_branch

        try:
            head = None
            """
            Example output:
8d621629e49230a973bd1fdaed1491d185d8bf32	HEAD
b5621dc553ee661480842cc284810b9c08af0911	refs/heads/git-clone-fix
8d621629e49230a973bd1fdaed1491d185d8bf32	refs/heads/master
de9dff53655734aa21357816897157161b238ad8	refs/merge-requests/3/merge
1a213d3af4dfa9cd068ff08dcd31ac08c4cf3e9c	refs/tags/last_known_good_version
            """
            for ref in subprocess.check_output(shlex_split("git ls-remote origin"), cwd = self._path, **spkwargs).splitlines():
                (sha, name) = ref.split()
                if name == "HEAD":
                    head = sha
                    continue
                if sha == head:
                    return name.rsplit("/", 1)[1]

            # An empty repository does not have a default branch
            return self.MASTER
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def __set_url(self, url):
        if not url.endswith(".git"):
            url += ".git"
        self._url = url

        return url


    def __initialize_if_empty(self, branch = None, gitignore_contents = "", initializer = None, verbose = True):
        """
        Initialize an empty repository
        """
        if not self.get_branches():
            # Try to set credential helper to cache (if not set) so users don't have to specify username/password twice
            try:
                helper = self.get_config("credential.helper", self._path)
                if not helper:
                    self.set_config("credential.helper", "cache")
            except Exception:
                # Not being able to set a credential helper is not fatal
                pass
            # Create a .gitignore file on 'master' so we can create a development branch
            if verbose:
                print("Initializing empty repository...")
            gitignore = os.path.join(self._path, ".gitignore")
            with open(gitignore, "wt") as gf:
                if gitignore_contents:
                    print(gitignore_contents, file = gf)
            self.add(gitignore)
            if initializer and callable(initializer):
                initializer(self)
            self.commit("Initialized repository")
            if branch is None:
                branch = self._default_branch
            self._branch = branch
            self.push()


    def __clone(self, url, branch = None, initialize_if_empty = False, verbose = True, gitignore_contents = "", initializer = None):
        """
        Clone 'url'. If branch is specified then that branch is checked out
        """
        try:
            if verbose:
                print("Cloning {}...".format(url))
            subprocess.check_output(shlex_split("git clone --quiet {} .".format(url)), cwd = self._path, stderr = subprocess.STDOUT, **spkwargs)
            self._default_branch = self.get_default_branch()
            self._branch = self._default_branch
            if initialize_if_empty:
                self.__initialize_if_empty(branch, gitignore_contents, initializer, verbose = verbose)

            if branch:
                if not self.get_branches():
                    raise GITException("Empty repository does not have branch '{}'".format(branch))
                self.checkout(branch)
        except subprocess.CalledProcessError as e:
            if e.output.strip().lower().startswith("fatal: destination path '.' already exists and is not an empty directory"):
                raise GITException("Directory '{}' already exists and is not a git repository".format(self._path))
            raise GITSubprocessException(e, self._path)


    def is_repo(self):
        return self.__is_repo(self._path)


    def checkout(self, branch = None):
        """
        Checks out 'branch'. If `branch` is None checks out the default branch
        """
        if branch is None:
            branch = self._default_branch

        if self._branch == branch:
            return self._branch

        try:
            subprocess.check_call(shlex_split("git checkout --quiet {}".format(branch)), cwd = self._path, **spkwargs)
            self._branch = branch
            return self._branch
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def create_branch(self, branch, start_point = None):
        """
        Creates and checks out 'branch' with starting point of 'start_point' (if specified)
        """
        try:
            if start_point:
                start_point = " {}".format(start_point)
            subprocess.check_output(shlex_split("git checkout --quiet -b {}{}".format(branch, start_point)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
            self._branch = branch
        except subprocess.CalledProcessError as e:
            if e.output.strip().lower().startswith("fatal: cannot update paths and switch to branch '{}' at the same time.".format(branch.lower())):
                raise GITException("Branch {} does not exist".format(start_point))
            raise GITSubprocessException(e, self._path)


    def get_branches(self):
        """
        Returns the hashes(?) of the available branches
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --branches"), cwd = self._path, **spkwargs).splitlines()
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def get_current_branch(self):
        """
        Returns the current branch
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def add(self, files):
        """
        Adds the files in 'files'
        """
        try:
            if isinstance(files, str):
                files = [files]
            file_paths = [os.path.normpath(x) for x in files]
            git_command = ["git", "add"] + file_paths
            return subprocess.check_call(git_command, cwd=self._path)
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def remove(self, files, ignore_unmatch = False):
        """
        Removes the files in 'files'. Works for absolute or WC-relative paths
        """
        try:
            if isinstance(files, str):
                files = [ files ]
            if ignore_unmatch:
                ignore_unmatch = "--ignore-unmatch "
            else:
                ignore_unmatch = ""
            return subprocess.check_call(shlex_split("git rm --quiet {}{}".format(ignore_unmatch, " ".join(map(lambda x: os.path.relpath(x, self._path) if os.path.isabs(x) else x, files)))), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def commit(self, msg = None, edit = False):
        """
        Commits the current contents of the index
        """
        try:
            if msg:
                msg = "-m '{msg}'{edit}".format(msg = msg, edit = ' --edit' if edit else '')
            else:
                msg = ""
            return subprocess.check_call(shlex_split("git commit --quiet {}".format(msg)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def remote_tags(self):
        """
        Returns the remote tags

        A list of lines as returned by 'git ls-remote --tags'
        """
        try:
            return subprocess.check_output(shlex_split("git ls-remote --tags origin"), cwd = self._path, **spkwargs).splitlines()
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def __filter_tag_names(self, ls_remote_output):
        """
        Removes the commit hashes and the refs/tags/ part of the tags. Also removes tags with the ^{} suffix
        """
        return filter(lambda x: not x.endswith("^{}"), map(lambda x: x[x.index("refs/tags/") + 10:], ls_remote_output))


    def tag(self, tag, msg = None, override_local = False):
        """
        Tags using 'msg' as commit message or 'tag' if 'msg' is not specified

        If 'override_local' is True it will overwrite existing _local_ tags
        """
        try:
            if msg is None:
                msg = tag
            msg = "-m '{}'".format(msg)

            if tag in self.__filter_tag_names(self.remote_tags()):
                raise GITException("Tag '{}' already exists".format(tag))
            else:
                if override_local:
                    force = "-f "
                else:
                    force = ""

            return subprocess.check_output(shlex_split("git tag -a {} {} {}".format(tag, force, msg)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            if e.output.strip().lower() == "fatal: tag '{}' already exists".format(tag.lower()):
                raise GITException("Tag '{}' already exists".format(tag))
            raise GITSubprocessException(e, self._path)


    def push(self, verbose = True):
        """
        Pushes the current branch

        Returns a URL to create a merge request
        """
        try:
            if verbose:
                print("Pushing your changes to {}...".format(self._url))
            subprocess.check_call(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), cwd = self._path, **spkwargs)
            if helpers.url_to_host(self._url) == "gitlab.esss.lu.se":
                return "{url}/-/merge_requests/new?merge_request%5Bsource_branch%5D={branch}".format(url = self._url[:-4], branch = self._branch)
            # For some reason subprocess will hang when trying to capture the 'remote:' messages
            # subprocess.run() is not available in Python2

#            lines = subprocess.check_output(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs).splitlines()

#            out = subprocess.run(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = self._path, **spkwargs)
#            print(out)
#            lines = out.stderr.splitlines()

#            out = subprocess.Popen(shlex_split("git push --follow-tags --porcelain origin {}".format(self._branch)), stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = self._path, **spkwargs)
#            print("out:", out)
#            print("Calling communicate()")
#            output, stderr = out.communicate()
#            print("Calling poll()...")
#            retcode = out.poll()
#            if retcode:
#                raise GITSubprocessException(subprocess.CalledProcessError(retcode, "git push", output = stderr), self._path)
#                raise subprocess.CalledProcessError(retcode, "git push", output = stderr)
#            print("STDOUT", output)
#            print("STDERR", stderr)
#            lines = stderr.splitlines()

#            print(lines)
#            lines = map(lambda l: l.strip()[GIT.REMOTE_PREFIX_LEN:].strip() if l.strip().startswith(GIT.REMOTE_PREFIX) else l.strip(), lines)
#            print(lines)
#            found = False
#            for l in lines:
#                if not l:
#                    continue
#
#                if l == "To create a merge request for {}, visit:".format(self._branch):
#                    print("Found",l)
#                    found = True
#                    continue
#
#                if found:
#                    # Return the link to merge request creation
#                    print("Link:", l)
#                    return l
            return None
        except subprocess.CalledProcessError as e:
            if e.output.strip().lower().startswith("fatal: authentication failed for "):
                raise GITException("AUTHENTICATION PROBLEM")
            raise GITSubprocessException(e, self._path)


    def fetch(self, src, dst = None):
        """
        Fetches 'src' into 'dst'
        """
        try:
            if dst:
                dst = ":" + dst
            subprocess.check_output(shlex_split("git fetch --quiet origin {}{}".format(src, dst)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def fetch_tags(self):
        """
        Fetches tags
        """
        try:
            subprocess.check_output(shlex_split("git fetch --quiet --tags origin"), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            raise GITSubprocessException(e, self._path)


    def pull(self, src = ""):
        """
        Pulls 'src'
        """
        try:
            subprocess.check_output(shlex_split("git pull --ff-only --quiet origin {}".format(src)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            err = e.output.strip().lower()
            if "your configuration specifies to merge with the ref" in err and "from the remote, but no such ref was fetched" in err:
                raise GITException("Deleted remote ref")
            raise GITSubprocessException(e, self._path)


    def remove_stale_items(self, current_items):
        """
        Removes files not staged for commit. Skips files in 'root' of working directory
        """
        # Get the 'toplevel' directories E3 creates
        paths = set()
        for cf in current_items:
            # Get a repository relative path
            relpath = os.path.relpath(cf, self.path())
            # Get the first component
            path = helpers.Path(relpath)
            path = path.parts[0]
            # Make sure that it is a directory
            if not os.path.isdir(os.path.join(self.path(), path)):
                continue
            paths.add(path)

        # Now check that every file under 'paths' is still relevant
        for path in paths:
            for root, dirs, files in os.walk(os.path.join(self.path(), path)):
                for f in files:
                    cur_f = os.path.join(root, f)
                    # Try with normalized path too to be safe
                    if os.path.normpath(cur_f) not in current_items and cur_f not in current_items:
                        self.remove(os.path.join(root, f), ignore_unmatch = True)





def get_status(cwd = None):
    # Returns True if clean
    if cwd is None:
        cwd = __git_dir
    try:
        return subprocess.check_output(shlex_split("git status -uno --porcelain"), cwd = __git_dir, **spkwargs).strip() == ""
    except subprocess.CalledProcessError:
        return False


def get_origin():
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --get-url origin"), cwd = __git_dir, **spkwargs)
        return output.strip()
    except subprocess.CalledProcessError:
        return None


def get_current_branch():
    try:
        return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = __git_dir, **spkwargs).strip()
    except subprocess.CalledProcessError:
        return None


def get_local_ref(branch = "master"):
    try:
        return subprocess.check_output(shlex_split("git rev-parse {}".format(branch)), cwd = __git_dir, **spkwargs).strip()
    except subprocess.CalledProcessError:
        return None


def get_remote_ref(branch = "master"):
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --quiet --exit-code origin refs/heads/{}".format(branch)), cwd = __git_dir, **spkwargs)
        return output[:-len("refs/heads/{}\n".format(branch))].strip()
    except subprocess.CalledProcessError:
        return None


def has_commit(commit):
    try:
        # Cannot use check_call; have to redirect stderr...
        subprocess.check_output(shlex_split("git cat-file -e {}^{{commit}}".format(commit)), stderr = subprocess.STDOUT, cwd = __git_dir, **spkwargs)
        return True
    except subprocess.CalledProcessError:
        return False


def check_for_updates(data_dir, product):
    local_ref = get_local_ref()

    if local_ref is None:
        print("Could not check local version")
        return False

    check_time = time.time()

    try:
        with open(os.path.join(data_dir, "updates")) as u:
            raw_updates = u.readline()
        from ast import literal_eval as ast_literal_eval
        updates = ast_literal_eval(raw_updates)
        if updates[0] + 600 > check_time:
            if local_ref != updates[1]:
                print("An update is available")
            return False
    except Exception:
        pass

    print("Checking for updates...")
    try:
        remote_ref = get_remote_ref()
    except KeyboardInterrupt:
        remote_ref = None
    if remote_ref is None:
        print("Could not check for updates")
        return False

    # Check if we have remote ref. True means we are most probably ahead of origin; ignore remote ref then
    if has_commit(remote_ref):
        remote_ref = local_ref

    updates = (check_time, remote_ref)
    try:
        with open(os.path.join(data_dir, "updates"), "w") as u:
            print(updates, file = u)
    except Exception:
        pass

    if remote_ref != local_ref:
        print("""
An update to {} is available.

Please run `git pull`
""".format(product))
        return True

    return False





if __name__ == "__main__":
    print("Local ref:", get_local_ref())
    print("Remote ref:", get_remote_ref())
