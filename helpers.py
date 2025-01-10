from __future__ import absolute_import

""" PLC Factory: helper functions """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import os
from shlex import split as shlex_split
import subprocess
import unicodedata
try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:
    from urlparse import urlsplit, urlunsplit

try:
    from urllib.parse import quote as urlquote, splituser
except ImportError:
    from urllib import quote as urlquote, splituser

try:
    from pathlib import Path
except ImportError:
    class FakePath(object):
        def __init__(self, p):
            self.parts = tuple(p.split(os.path.sep))
    Path = FakePath


from posixpath import join as posixpathjoin

# Fake a WindowsError exception under non-Windows machines
try:
    we = WindowsError()
    del we
except NameError:
    WindowsError = OSError

# Fake a FileNotFoundError in Python2
try:
    fnf = FileNotFoundError()
    del fnf
    FileNotFoundError = FileNotFoundError
except NameError:
    FileNotFoundError = OSError



class BusyException(OSError):
    pass


def rmdirs(path):
    #
    # Python3(.6?) has a weird interaction with VirtualBox shared folders where shutil.rmtree returns OSError(26) (text file busy) errors
    # So we, check if the exception is OSError(26) and handle that outside of shutil.rmtree() with os.rmdir() and then retry shutil.rmtree
    #
    
    from shutil import rmtree
    def onrmtreeerror(func, e_path, exc_info):
        if exc_info[0] is OSError and exc_info[1].errno == 26:
            be = BusyException(exc_info[1])
            be.filename = e_path
            raise be

        if e_path != path:
            raise

        if not (func is os.listdir or func is os.rmdir or func is os.lstat or func is os.scandir):
            raise

        if not (exc_info[0] is OSError or exc_info[0] is FileNotFoundError or exc_info[0] is WindowsError):
            raise

        if exc_info[1].errno != 2:
            raise

    while True:
        try:
            rmtree(path, onerror = onrmtreeerror)
            return
        except BusyException as e:
            os.rmdir(e.filename)


def makedirs(path):
    """
    Helper that ignores already existing directory error
    """
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def sanitize_path(path):
    """
    Helper that sanitizes path; replaces accented characters and removes invalid ones
    """
    path = tounicode(path)

    # replace accented characters with the unaccented equivalent
    path = unicodedata.normalize("NFKD", path).encode("ASCII", "ignore")

    if isinstance(path, bytes) and not isinstance(path, str):
        # Only needed for Python3
        path = path.decode()

    invalid_chars = '<>:"/\\|?*'
    def sanP(p):
        (head, tail) = os.path.split(p)
        if not head:
            return "".join(map(lambda x: '_' if x in invalid_chars else x, p))
        tail = "".join(map(lambda x: '_' if x in invalid_chars else x, tail))
        return os.path.join(sanP(head), tail)

    return sanP(path)


def sanitizeFilename(filename):
    """
    Helper that sanitizes filename; replaces accented characters and removes invalid ones

    It will also replace path separators!
    """
    filename = tounicode(filename)

    # replace accented characters with the unaccented equivalent
    filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore")

    if isinstance(filename, bytes) and not isinstance(filename, str):
        # Only needed for Python3
        filename = filename.decode()

    invalid_chars = '<>:"/\\|?*'
    return "".join(map(lambda x: '_' if x in invalid_chars else x, filename))


def create_cache_dir(product, dirs = None):
    """
    Creates 'cache directory' under ~/.cache
    """
    dname = os.path.join(os.path.expanduser("~"), ".cache", product)
    if dirs is not None:
        dname = os.path.join(dname, dirs)
    makedirs(dname)

    return dname


def create_data_dir(product, dirs = None):
    """
    Creates 'data directory' under ~/.local/share
    """
    dname = os.path.join(os.path.expanduser("~"), ".local", "share", product)
    if dirs is not None:
        dname = os.path.join(dname, dirs)
    makedirs(dname)

    return dname


def tounicode(string):
    """
    Converts string to unicode (Not needed for Python3)
    """
    try:
        # Python2 shortcut
        if isinstance(string, unicode):
            return string
    except NameError:
        # Python3, it is already unicode
        return string

    return string.decode("utf-8")


def url_strip_user(url):
    """
    Removes the 'username@' part of a URL


    https://krisztianloki@gitlab.esss.lu.se/icshwi/plcfactory.git ==> https://gitlab.esss.lu.se/icshiw/plcfactory.git
    """
    comps = urlsplit(url)
    netloc = splituser(comps.netloc)[1]
    return urlunsplit((comps[0], netloc, comps[2], comps[3], comps[4]))


def url_to_path(url):
    """
    Returns the url without the protocol sanitized (invalid characters removed) as a path


    https://gitlab.esss.lu.se/icshwi/linac-vac-plc-def/raw/master/blob/VACUUM_VAC-PLCIO.def ==> gitlab.esss.lu.se/icshwi/linac-vac-plc-def/raw/master/blob/VACUUM_VAC-PLCIO.def
    """

    comps = urlsplit(url)
    comps = splituser(comps.netloc)[1] + comps.path
    comps = comps.split('/')

    return os.path.join(*map(lambda sde: sanitizeFilename(sde), comps))


def url_to_host(url):
    """
    Returns the host part of the url

    https://gitlab.esss.lu.se/icshwi/plcfactory.git ==> gitlab.esss.lu.se
    """

    return splituser(urlsplit(url).netloc)[1]


def urljoin(part1, part2, *more):
    """
    Join paths to form a URL

    NOT using urljoin because it ignores any path component in part1
    """
    if part2[0] == '/':
        part2 = part2[1:]

    if more:
        part2 = posixpathjoin(part2, *[ m[1:] if m[0] =='/' else m for m in more])

    return posixpathjoin(part1, part2)


def sanitize_url(url):
    """
    Sanitizes URLs (removes double //)
    """
    parts = list(urlsplit(url))

    while "//" in parts[2]:
        parts[2] = parts[2].replace("//", "/")

    return urlunsplit(parts)


def xdg_open(url):
    try:
        subprocess.check_call(shlex_split("xdg-open {}".format(url)))
    except (OSError, FileNotFoundError) as e:
        if e.errno == 2:
            raise FileNotFoundError(e)

        raise

