from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import getpass
try:
    import requests
except ImportError:
    raise NotImplementedError("""
++++++++++++++++++++++++++++++++++++
Could not find package 'requests'!
Please install it by running

sudo yum install python-requests

++++++++++++++++++++++++++++++++++++
""")
from collections import OrderedDict
from os import path as os_path
from shutil import copy2


# disable printing of unsigned SSH connection warnings to console
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# PLC Factory modules
import helpers
import levenshtein
import plcf_git as git



class CC(object):
    TEMPLATE_DIR    = "templates"
    TAG_SEPARATOR   = "__"
    GIT_SUFFIX      = ".git"
    CCDB_ZIP_SUFFIX = ".ccdb.zip"
    DEVICE_DICT     = "device.dict"
    DEVICE_JSON     = "device.json"
    DEVICE_YAML     = "device.yaml"
    GIT_CACHE       = "data-model"
    paths_cached    = dict()
    sessions_cached = dict()


    class Exception(Exception):
        """Base class for Controls and Configuration exceptions"""
        def __str__(self):
            if self.message:
                return """
{banner}
{msg}
{banner}
""".format(banner = "*" * max(map(lambda x: len(x), str(self.message).splitlines())), msg = self.message)
            else:
                return super(CC.Exception, self).__str__()



    class DownloadException(Exception):
        def __init__(self, url, code):
            super(CC.DownloadException, self).__init__()
            self.url  = url
            self.code = code
            if url is not None:
                self.message = "Cannot download {url}: error {code}".format(url = self.url, code = self.code)



    class ArtifactException(DownloadException):
        def __init__(self, dloadexception, deviceName = None, filename = None):
            self.deviceName = deviceName
            self.filename   = filename

            if isinstance(dloadexception, CC.DownloadException):
                super(CC.ArtifactException, self).__init__(url = dloadexception.url, code = dloadexception.code)
                self.message = "Cannot get artifact {art} of {device}: error {code} ({url})".format(device = self.deviceName,
                                                                                                    art    = self.filename,
                                                                                                    code   = self.code,
                                                                                                    url    = self.url)
            else:
                super(CC.ArtifactException, self).__init__(None, None)
                self.message = dloadexception



    class NoSuchDeviceException(Exception):
        pass



    class BasicAuth(requests.auth.AuthBase):
        def __init__(self, username = None):
            super(CC.BasicAuth, self).__init__()

            if username is None:
                username = getpass.getuser()
            self.username = username
            self.password = None


        def __eq__(self, other):
            return all([
                        self.username == getattr(other, 'username', None),
                        self.password == getattr(other, 'password', None)
                       ])


        def __ne__(self, other):
            return not self == other


        def __call__(self, r):
            if not self.password:
                self.password = getpass.getpass("Password of {} for {}: ".format(self.username, r.url.split('?')[0]))
            r.headers['Authorization'] = requests.auth._basic_auth_str(self.username, self.password)
            return r


        def isvalid(self):
            return self.password is not None



    class Artifact(object):
        __REPOS_CACHED    = dict()


        def __init__(self, device):
            super(CC.Artifact, self).__init__()

            self._device = device

            self.reset_saveas()

            # EPI, ALARM TREE, etc
            if self.is_uri():
                self._app_type = self.name().split('[')[0]
            else:
                self._app_type = None


        def __repr__(self):
            return self.name()


        def __not_perdevtype(self):
            """
            This one is used in place of is_perdevtype if _saveasversion is device specific
            """
            return False


        def reset_saveas(self):
            """
            Before downloadExternalLink the _saveas* variables need to be reset to None
            """
            self._saveas         = None
            self._saveasurl      = None
            self._saveasversion  = None
            if self.is_file():
                self._saveasversion_is_default = True
                self._saveasfilename = self.filename()
            else:
                self._saveasversion_is_default = None
                self._saveasfilename = None


        def registerDownloadedArtifact(self, filename):
            self._device.registerDownloadedArtifact(filename)


        def name(self):
            raise NotImplementedError


        def is_file(self):
            raise NotImplementedError


        def is_uri(self):
            raise NotImplementedError


        def is_perdevtype(self):
            raise NotImplementedError


        def filename(self):
            raise NotImplementedError


        def uri(self):
            raise NotImplementedError


        def uniqueID(self):
            raise NotImplementedError


        def app_type(self):
            if self._app_type is None and not self.is_uri():
                raise NotImplementedError

            return self._app_type


        def __register_git_repo(self, wc):
            """
                Register that this artifact's url was cloned and `wc` is the GIT object.
            """
            CC.Artifact.__REPOS_CACHED[self.saveas_url()] = wc


        def __is_git_repo_registered(self):
            """
                Returns True if this artifact's url is registered as cloned
            """
            return self.saveas_url() in CC.Artifact.__REPOS_CACHED


        def __get_registered_git_repo(self):
            """
                Returns the GIT object that was cloned for this artifact
            """
            return CC.Artifact.__REPOS_CACHED[self.saveas_url()]


        def __get_git_working_copy(self):
            if not self.is_uri():
                raise CC.ArtifactException("Artifact is not a git link")

            if self.__is_git_repo_registered():
                wc = self.__get_registered_git_repo()
            else:
                wcdir = os_path.join(self._device.ccdb.GIT_CACHE, CC.url_to_path(self.saveas_url()))
                helpers.makedirs(wcdir)
                wc = git.GIT.clone(self.saveas_url(), wcdir, branch = self.saveas_version(), update = True)

                self.__register_git_repo(wc)

            return wc


        def __get_git_default_branch(self):
            if self.saveas_version() is not None:
                raise CC.ArtifactException("Artifact needs non-default branch!")

            return self.__get_git_working_copy().get_default_branch()


        def __git_download(self):
            try:
                copy2(os_path.join(self.__get_git_working_copy().path(), self.saveas_filename()), self.saveas())
            except IOError as e:
                if e.errno == 2:
                    raise CC.DownloadException(self.uri(), "*404")

                raise


        def saveas(self):
            """
            Returns the full path (relative to the current directory) of the downloaded artifact filename
            """
            if self._saveas is None:
                # NOTE: we _must not_ use CC.TEMPLATE_DIR here,
                # CCDB_Dump relies on creating an instance variant of TEMPLATE_DIR to point it to its own templates directory
                if self.is_file():
                    self._saveas = CC.saveas(self.uniqueID(), self.saveas_filename(), self._device.ccdb.TEMPLATE_DIR)
                else:
                    self._saveas = CC.saveas(self.uniqueID(), self.saveas_filename(), os_path.join(self._device.ccdb.TEMPLATE_DIR, CC.url_to_path(self.saveas_url()), self.saveas_version()))

            return self._saveas


        def _set_saveas_url(self, url):
            self._saveasurl = url


        def _determine_saveas_url(self):
            """
            Should set self._saveasurl to the URL from where the artifact can be/was downloaded
            """
            if self.is_uri():
                url = self.uri()
                if not url.endswith(CC.GIT_SUFFIX) and helpers.url_to_host(url) != "bitbucket.org":
                    url += CC.GIT_SUFFIX

                return url


        def saveas_url(self):
            """
            Returns the full url from where the artifact has to be downloaded
            """
            if self._saveasurl is None:
                self._set_saveas_url(self._determine_saveas_url())
                if self._saveasurl is None:
                    raise NotImplementedError

            return self._saveasurl


        def set_saveas_version(self, version):
            if version is None:
                self._saveasversion_is_default = True
            else:
                self._saveasversion_is_default = False
                self._saveasversion = version


        def saveas_version(self):
            """
            Returns the version that needs to be downloaded (the branch/tag if git repo)
            """
            if self._saveasversion is None and self._saveasversion_is_default is None:
                raise NotImplementedError

            return self._saveasversion


        def saveas_filename(self):
            if self._saveasfilename is None:
                raise NotImplementedError

            return self._saveasfilename


        def defaultFilename(self, extension):
            return self._device.defaultFilename(extension)


        def __downloadExternalLink(self, extension = None, git_tag = None, filetype = None):
            if filetype is None:
                filetype = "External Link"

            linkfile  = self.name()

            # Check for explicit filename specification: SOMETHING[filename]
            open_bra = linkfile.find('[')
            if open_bra != -1:
                if linkfile[-1] != ']':
                    raise CC.ArtifactException("Invalid name format in External Link for {device}: {name}".format(device = self._device.name(), name = linkfile), self._device.name(), linkfile)

                filename = linkfile[open_bra + 1 : -1]
                if extension is not None:
                    if not extension.startswith('.'):
                        extension = '.{}'.format(extension)
                    if not filename.endswith(extension):
                        filename += extension

                # Check if the specified filename is valid
                if os_path.normpath(filename) != helpers.sanitize_path(filename):
                    raise CC.ArtifactException("Invalid filename in External Link for {device}: {name}".format(device = self._device.name(), name = filename), self._device.name(), filename)
            else:
                filename = self.defaultFilename(extension)

            self._saveasfilename = filename

            self._set_saveas_url(self._determine_saveas_url())

            if git_tag is None:
                version_prop = self._device.properties().get(self.app_type() + " VERSION", None)
                devtype_version_prop = self._device.devtypeProperties().get(self.app_type() + " VERSION", None)

                # if devtype_version_prop differs from version_prop it means that "app_type() VERSION" is a slot property ---> non per-devtype
                #  (becase a you cannot have a slot and device type property with the same name in CCDB)
                if version_prop != devtype_version_prop:
                    self.is_perdevtype = self.__not_perdevtype

                git_tag = version_prop
                self.set_saveas_version(git_tag)
                if git_tag is None:
                    git_tag = self.__get_git_default_branch()

            print("Downloading {filetype} file {filename} (version {version}) from {url}".format(filetype = filetype,
                                                                                                 filename = self.saveas_filename(),
                                                                                                 url      = self.uri(),
                                                                                                 version  = "<default>" if git_tag is None else git_tag))

            self.set_saveas_version(git_tag)


        def _download(self):
            if self.is_uri():
                return self.__git_download()

            raise NotImplementedError


        def download(self, extension = None, git_tag = None, filetype = None):
            """
            Returns a DownloadedArtifact or None
            """
            if self.is_uri():
                self.__downloadExternalLink(extension, git_tag, filetype)

            self._set_saveas_url(self._determine_saveas_url())
            save_as = self.saveas()

            # check if filename has already been downloaded
            if not os_path.exists(save_as):
                try:
                    self._download()
                except CC.DownloadException as e:
                    raise CC.ArtifactException(e, deviceName = self._device.name(), filename = self.saveas_filename())

            self.registerDownloadedArtifact(save_as)

            return CC.DownloadedArtifact(self)



    class DownloadedArtifact(object):
        def __init__(self, artifact):
            super(CC.DownloadedArtifact, self).__init__()

            self._epi            = None if artifact.is_file() else artifact.name()
            self._epi_url        = None if artifact.is_file() else artifact.uri()
            self._epi_version    = None if artifact.is_file() else artifact._saveasversion
            self._filename       = artifact.saveas_filename()
            self._url            = artifact.saveas_url()
            self._saved_as       = artifact.saveas()
            self._perdevtype     = artifact.is_perdevtype()


        # Not really sure that _perdevtype is needed; Artifact.download() uses saveas() ie _saved_as only
        def __eq__(self, other):
            return self._saved_as == other._saved_as and self._perdevtype == other._perdevtype


        def __hash__(self):
            return hash((self._saved_as, self._perdevtype))


        def saved_as(self):
            return self._saved_as


        def filename(self):
            return self._filename


        def url(self):
            return self._url


        def epi(self):
            return self._epi


        def epi_url(self):
            return self._epi_url


        def epi_version(self):
            return self._epi_version


        def is_perdevtype(self):
            return self._perdevtype



    class DeviceType(object):
        ccdb = None

        def __init__(self, ccdb):
            super(CC.DeviceType, self).__init__()

            if ccdb is not None:
                self.ccdb = ccdb


        def __str__(self):
            return self.name()


        def name(self):
            raise NotImplementedError


        def url(self):
            return None



    class Device(object):
        ccdb = None

        def __init__(self, ccdb):
            super(CC.Device, self).__init__()

            self._inControlledTree = False
            if ccdb is not None:
                self.ccdb = ccdb


        def __str__(self):
            return self.name()


        def to_yaml(self):
            """
            Returns the Python object that should be serialized into YAML
            """
            return str(self)


        def to_json(self):
            """
            Returns the Python object that should be serialized into JSON
            """
            return str(self)


        def url(self):
            return None


        def registerDownloadedArtifact(self, filename):
            self.ccdb._downloadedArtifacts.add(filename)


        @staticmethod
        def _ensure(var, default, convert_to_default = True):
            #
            # Do not return None
            #
            if var is not None:
                if isinstance(var, default) or not convert_to_default:
                    return var
                return default(var)

            return default()


        # Returns: {}
        def keys(self):
            raise NotImplementedError


        # Returns: ""
        def name(self):
            raise NotImplementedError


        # Returns: DeviceType
        def type(self):
            raise NotImplementedError


        def putInControlledTree(self):
            self._inControlledTree = True


        def isInControlledTree(self):
            return self._inControlledTree


        # Returns: []
        def controls(self, convert = True):
            return self._ensure(self._controls(), list, convert)


        # Returns: []
        def controlledBy(self, filter_by_controlled_tree = False, convert = True):
            ctrldBy = self._controlledBy(filter_by_controlled_tree)
            if not filter_by_controlled_tree:
                return self._ensure(ctrldBy, list, convert)
            return self._ensure(filter(lambda d: d.isInControlledTree(), ctrldBy), list, convert)


        # Returns: {}
        def properties(self, convert = True):
            return self._ensure(self._properties(), dict, convert)


        # Returns: {}
        def propertiesDict(self, prefixToIgnore = True):
            return self._ensure(self._propertiesDict(), dict)


        # Returns: {}
        def devtypeProperties(self, convert = True):
            return self._ensure(self._devtypeProperties(), dict, convert)


        # Returns: ""
        def deviceType(self):
            return self._ensure(self._deviceType(), str)


        # Returns: ""
        def description(self):
            return self._ensure(self._description(), str)


        # Returns: []
        def artifacts(self, convert = True):
            return self._ensure(self._artifacts(), list, convert)


        # Returns: []
        def artifactNames(self, convert = True):
            return self._ensure(map(lambda an: an.name(), filter(lambda fa: fa.is_file(), self.artifacts(convert = False))), list, convert)


        # Returns: []
        def externalLinks(self, convert = True):
            return self._ensure(filter(lambda u: u.is_uri(), self.artifacts(convert = False)), list, convert)


        # Returns: ""
        def backtrack(self, prop, ex_to_raise = None):
            return self._ensure(self._backtrack(prop, ex_to_raise), str)


        def defaultFilename(self, extension):
            if extension is None:
                extension = ""
            elif not extension.startswith('.'):
                extension = '.{}'.format(extension)

            return helpers.sanitizeFilename(self.deviceType().upper() + extension)


        def __splitDefs(self, defs):
            # Separate device and device type artifacts
            devtype_defs = []
            dev_defs     = []
            for art in defs:
                if art.is_perdevtype():
                    devtype_defs.append(art)
                else:
                    dev_defs.append(art)

            return (dev_defs, devtype_defs)


        def downloadArtifact(self, extension, device_tag = None, filetype = '', custom_filter = None, filter_args = ()):
            """
            Returns a DownloadedArtifact or None
            """
            if custom_filter is None:
                def filter_device_tags(artifact):
                    return CC.TAG_SEPARATOR not in artifact.filename()

                def no_filter(artifact):
                    return True

                if not extension.startswith('.'):
                    extension = '.{}'.format(extension)

                if device_tag:
                    # whatever__devicetag.extension
                    suffix = "".join([ CC.TAG_SEPARATOR, device_tag, extension ])
                    custom_filter = no_filter
                else:
                    suffix = extension
                    custom_filter = filter_device_tags

                defs = filter(lambda a: a.is_file() and a.filename().endswith(suffix) and custom_filter(a), self.artifacts())
            else:
                defs = filter(lambda a: a.is_file() and custom_filter(a, *filter_args), self.artifacts())

            # Separate device and device type artifacts
            (dev_defs, devtype_defs) = self.__splitDefs(defs)

            def __checkArtifactList(defs):
                if not defs:
                    return None

                if len(defs) > 1:
                    raise CC.ArtifactException("More than one {filetype} Artifacts were found for {device}: {defs}".format(filetype = filetype, device = self.name(), defs = defs), self.name())

                print("Downloading {filetype} file {filename} from CCDB".format(filetype = filetype,
                                                                                filename = defs[0].filename()))

                defs[0].reset_saveas()
                return defs[0].download()

            # device artifacts have higher priority than device type artifacts
            art = __checkArtifactList(dev_defs)
            if art is not None:
                return art

            return __checkArtifactList(devtype_defs)


        def downloadExternalLink(self, base, extension, device_tag = None, filetype = 'External Link', git_tag = None):
            """
            Returns a DownloadedArtifact or None
            """
            if not extension.startswith('.'):
                extension = '.{}'.format(extension)

            if device_tag:
                # base__devicetag
                base = CC.TAG_SEPARATOR.join([ base, device_tag ])

            artifacts = filter(lambda u: u.is_uri() and u.app_type() == base, self.artifacts())

            # Separate device and device type external links
            (dev_defs, devtype_defs) = self.__splitDefs(artifacts)

            def __checkExternalLinkList(defs):
                if not defs:
                    return None

                if len(defs) > 1:
                    raise CC.ArtifactException("More than one {filetype} External Links were found for {device}: {urls}".format(filetype = filetype, device = self.name(), urls = list(map(lambda u: u.uri(), defs))), self.name())

                defs[0].reset_saveas()
                return defs[0].download(extension, git_tag = git_tag, filetype = filetype)

            # device external links have higher priority than device type external links
            art = __checkExternalLinkList(dev_defs)
            if art is not None:
                return art

            return __checkExternalLinkList(devtype_defs)


        # returns a stable list of controlled devices
        # Returns: []
        def buildControlsList(self, include_self = False, verbose = False):
            self.putInControlledTree()

            # find devices this device _directly_ controls
            pool = self.controls()

            # find all devices that are directly or indirectly controlled by 'device'
            controlled_devices = set(pool)
            while pool:
                dev = pool.pop()

                cdevs = dev.controls()
                for cdev in cdevs:
                    if cdev not in controlled_devices:
                        controlled_devices.add(cdev)
                        pool.append(cdev)

            # group them by device type
            pool = list(controlled_devices)
            controlled_devices = dict()
            for dev in pool:
                device_type = dev.deviceType()
                try:
                    controlled_devices[device_type].append(dev)
                except KeyError:
                    controlled_devices[device_type] = [ dev ]

            if verbose:
                if verbose is True:
                    print("\r" + "#" * 60)
                    print("Device at root: " + self.name() + "\n")
                    print(self.name() + " controls: ")
                else:
                    verbose(self, 'root')

            # sort items into a list
            def sortkey(device):
                return device.name()
            pool = list()
            for device_type in sorted(controlled_devices):
                if verbose:
                    if verbose is True:
                        print("\t- " + device_type)
                    else:
                        verbose(controlled_devices[device_type][0].type(), 'device_type')

                for dev in sorted(controlled_devices[device_type], key=sortkey):
                    pool.append(dev)
                    dev.putInControlledTree()
                    if verbose:
                        if verbose is True:
                            print("\t\t-- " + dev.name())
                        else:
                            verbose(dev, 'device')

            if verbose is True:
                print("\n")

            if include_self:
                pool.insert(0, self)

            return pool


        def toFactory(self, filename, directory = ".", git_tag = None, script = None):
            return self.ccdb.toFactory(filename, directory, git_tag = git_tag, root = self, script = script)



    def __init__(self, clear_templates = True):
        super(CC, self).__init__()

        self._clear_templates = clear_templates
        self.__clear()


    @staticmethod
    def addArgs(parser):
        ccdb_args = parser.add_argument_group("CCDB related options")

        ccdb_args.add_argument(
                                  '--ccdb',
                                  dest     = "ccdb",
                                  help     = 'use a CCDB dump or custom URL as backend',
                                  metavar  = 'directory-to-CCDB-dump / name-of-.ccdb.zip / URL to CCDB server',
                                  type     = str,
                                  required = False)

        ccdb_args.add_argument(
                               '--cached',
                               dest     = "clear_ccdb_cache",
                               help     = 'do not clear "templates" folder; use the templates downloaded by a previous run',
                               # be aware of the inverse logic between the meaning of the option and the meaning of the variable
                               default  = True,
                               action   = 'store_false')

        return parser


    @staticmethod
    def urlsplit(url):
        return helpers.urlsplit(url)


    @staticmethod
    def urlquote(string):
        return helpers.urlquote(string)


    @staticmethod
    def url_to_path(url):
        return helpers.url_to_path(url)


    @staticmethod
    def urljoin(base, path, *more):
        return helpers.urljoin(base, path, *more)


    @staticmethod
    def saveas(uniqueID, filename, directory, CreateDir = True):
        try:
            return CC.paths_cached[uniqueID, filename, directory]
        except KeyError:
            dtdir = os_path.join(directory, helpers.sanitize_path(uniqueID))
            path = os_path.join(dtdir, helpers.sanitize_path(filename))
            if CreateDir:
                helpers.makedirs(os_path.dirname(path))

            path = os_path.normpath(path)
            CC.paths_cached[uniqueID, filename, directory] = path

            return path


    @staticmethod
    def tostring(string):
        if isinstance(string, str) or string is None:
            return string

        if isinstance(string, list):
            return [CC.tostring(s) for s in string]

        if isinstance(string, dict):
            newdict = dict()
            for k in string:
                newdict[CC.tostring(k)] = CC.tostring(string[k])

            return newdict

        if isinstance(string, int):
            return str(string)

        try:
            # Have to check for unicode type in Python2
            # isinstance(string, str) above is enough in Python3
            if not isinstance(string, unicode):
                raise CC.Exception("Unhandled type {}: {}".format(type(string), string))
        except NameError:
            # Sadly, the 'from None' part is not valid in Python2
            raise CC.Exception("Unhandled type {}: {}".format(type(string), string))  # from None

        try:
            return string.encode("unicode-escape").decode("string-escape").decode("utf-8").encode("utf-8")
        except UnicodeDecodeError:
            return string.encode("utf-8")


    @staticmethod
    def get(url, auth = None, **keyword_params):
        netloc = CC.urlsplit(url).netloc

        try:
            (session, auth) = CC.sessions_cached[netloc]
        except KeyError:
            session = requests.session()
            if auth is None:
                auth    = CC.BasicAuth()
            CC.sessions_cached[netloc] = (session, auth)

        # Try without authentication first; don't want to bother users with asking for their password when not really needed
        result = session.get(url, auth = auth if auth.isvalid() else None, **keyword_params)
        if result.status_code == 401:
            result = session.get(url, auth = auth, **keyword_params)

        return result


    @staticmethod
    def download(url, save_as, verify_ssl_cert = True, **keyword_params):
        result = CC.get(url, verify = verify_ssl_cert, **keyword_params)

        if result.status_code != 200:
            raise CC.DownloadException(url = url, code = result.status_code)

        # 'w' overwrites the file if it exists
        with open(save_as, 'wb') as f:
            for line in result:
                f.write(line)

        return save_as


    def __clear(self):
        # all devices; key, Device pairs
        self._devices = OrderedDict()

        # cache for device, property dictionary
        self._propDict = dict()

        # cache for ^() expressions
        # key: (device, expression), value: property
        self._backtrackCache = dict()

        # cache of downloaded artifacts
        self._downloadedArtifacts = set()

        if self._clear_templates:
            # clear templates downloaded in a previous run
            helpers.rmdirs(CC.TEMPLATE_DIR)
            CC.paths_cached = dict()
        else:
            print("Reusing templates of any previous run")

        helpers.makedirs(CC.TEMPLATE_DIR)
        self.GIT_CACHE = helpers.create_cache_dir("ccdb", CC.GIT_CACHE)


    # clear whatever we have. let other implementations override
    def clear(self):
        self.__clear()


    def url(self):
        return None


    def _get_device(self, devicename, single_device_only):
        """
        Should return a CC.Device
        """
        raise NotImplementedError


    # Returns: CC.Device
    def device(self, deviceName, cachedOnly = False, single_device_only = False):
        try:
            return self._devices[self.deviceName(deviceName)]
        except KeyError:
            if cachedOnly:
                return None

            device = self._get_device(deviceName, single_device_only = single_device_only)
            device.ccdb = self

            return device


    # Returns: the device name
    # CCDB returns a dictionary of {nameId, Id, name} in controls/controlledBy/etc list
    def deviceName(self, deviceName):
        return deviceName


    # Returns: {}
    def _propertiesDict(self, device, prefixToIgnore = "PLCF#"):
        # Not using 'if prefixToIgnore:' because we really want to check if it is a boolean and true
        if prefixToIgnore is True:
            prefixToIgnore = "PLCF#"

        if prefixToIgnore == "":
            return device.properties()

        deviceName = device.name()

        if (deviceName, prefixToIgnore) in self._propDict:
            return self._propDict[deviceName, prefixToIgnore]

        result = {}
        for (name, value) in device.properties().items():
            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            result[name] = value

        self._propDict[deviceName, prefixToIgnore] = result

        return result


    # Returns: []
    def getAllDeviceNames(self):
        raise NotImplementedError


    # Returns: []
    def getSimilarDeviceNames(self, deviceName, X = 10):
        """
            Returns the topX most similar device names in the database

            Returns a tuple (filtered, topX):
             - filtered; boolean if the list is filtered to the same System-Subsystem as deviceName
             - topX; a list of device names
        """
        allDevices = self.getAllDeviceNames()

        # keep only device
        slot = deviceName.split(":")
        candidates = None
        if len(slot) > 1:
            slot = slot[0].lower()
            candidates = list(filter(lambda x: x.lower().startswith(slot), allDevices))
            filtered = True

        if not candidates:
            candidates = allDevices
            filtered = False

        # compute Levenshtein distances
        candidates = list(map(lambda f: f[1], sorted(map(lambda x: (levenshtein.distance(deviceName, x), x), candidates))[:X]))

        return (filtered, candidates)


    def toFactory(self, filename, directory = ".", git_tag = None, script = None, root = None):
        devtypes      = []
        fact_devtypes = []
        fact_root     = []
        fact_devs     = []

        setProperty_str = """{var}.setProperty("{k}", {v})"""

        def setProperty(out, dev, var):
            comment = False
            for (k, v) in dev.properties().items():
                if not comment:
                    comment = True
                    out.append("# Properties")
                # FIXME: we really shouldn't pass 'null' instead of None... but that is what CCDB gives us, so...
                if v is None:
                    v = "null"
                elif isinstance(v, str):
                    v = '"{}"'.format(v)
                out.append(setProperty_str.format(var = var,
                                                  k   = k,
                                                  v   = v))

        def addDevice(dev, fact, var, output):
            devType = dev.deviceType()
            if devType == "PLC":
                output.append("""#
# Adding PLC: {device}
#
{var} = {fact}.addPLC("{device}")""".format(var = var, fact = fact, device = dev.name()))
            elif devType == "PLC_BECKHOFF":
                output.append("""#
# Adding Beckhoff PLC: {device}
#
{var} = {fact}.addBECKHOFF("{device}")""".format(var = var, fact = fact, device = dev.name()))
            else:
                output.append("""#
# Adding device {device} of type {type}
#
{var} = {fact}.addDevice("{type}", "{device}")""".format(var = var, fact = fact, type = devType, device = dev.name()))

            setProperty(output, dev, var)

            comment = False
            for elink in dev.externalLinks():
                if not elink.is_perdevtype():
                    if not comment:
                        comment = True
                        output.append("# External links")
                    output.append("""{var}.addLink("{name}", "{link}")""".format(var     = var,
                                                                                 name    = elink.name(),
                                                                                 link    = elink.uri()))

            comment = False
            for art in dev.artifacts():
                if not art.is_perdevtype() and art.is_file():
                    if not comment:
                        comment = True
                        output.append("# Artifacts")
                    output.append("""{var}.addArtifact("{name}")""".format(var  = var,
                                                                           name = art.name()))

            output.append('')

        def ctrls(device, var, idx = None):
            cvar = "{}{}".format(var, idx) if idx else "dev"
            idx  = idx + 1 if idx else 1
            for dev in device.controls():
                addDevice(dev, var, cvar, fact_devs)
                ctrls(dev, cvar, idx)

        # Define device type external links
        plc = None
        for devname in sorted(self._devices.keys()):
            dev      = self.device(devname)
            devType  = dev.deviceType()
            exLinks  = sorted(dev.externalLinks(), key = lambda x: x.name())

            if devType not in devtypes:
                if root is None and (devType == "PLC" or devType == "PLC_BECKHOFF"):
                    if plc:
                        raise CC.Exception("Cannot determine root device")
                    plc = dev

                devtypes.append(devType)

                newline = False
                comment = False
                for elink in exLinks:
                    if elink.is_perdevtype():
                        if not comment:
                            comment = True
                            fact_devtypes.append("""# External links for {}""".format(devType))
                        fact_devtypes.append("""factory.addLink("{devtype}", "{name}", "{link}")""".format(devtype = devType,
                                                                                                           name    = elink.name(),
                                                                                                           link    = elink.uri()))

                newline = comment
                comment = False
                for art in dev.artifacts():
                    if art.is_perdevtype() and art.is_file():
                        if not comment:
                            comment = True
                            fact_devtypes.append("# Artifacts for {}".format(devType))
                        fact_devtypes.append("""factory.addArtifact("{devtype}", "{name}")""".format(devtype = devType,
                                                                                                     name    = art.name()))

                if newline or comment:
                    fact_devtypes.append('')

        if root is None:
            root = plc

        if root is None:
            raise CC.Exception("Cannot determine root device")

        rootType = root.deviceType()
        if rootType == "IOC":
            root_var = "ioc"
        elif rootType == "PLC" or rootType == "PLC_BECKHOFF":
            root_var = "plc"
        else:
            root_var = "root"

        addDevice(root, "factory", root_var, fact_root)
        ctrls(root, root_var)

        fact = """#!/usr/bin/env python2

import os
import sys

sys.path.append(os.path.curdir)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ccdb_factory import CCDB_Factory

factory = CCDB_Factory({factory_options})

{links}
{root}
{devs}

#
# Saving the created CCDB
#
factory.save("{filename}")""".format(factory_options = 'git_tag = "{}"'.format(git_tag) if git_tag is not None else "",
                                     links           = "\n".join(fact_devtypes),
                                     root            = "\n".join(fact_root),
                                     devs            = "\n".join(fact_devs),
                                     filename        = filename)

        if script is None:
            script = filename

        if not script.endswith("_ccdb.py"):
            script += "_ccdb.py"

        script = os_path.join(directory, helpers.sanitize_path(script))
        with open(script, "w") as f:
            print(fact, file = f)

        return script


    def dump(self, filename, directory = "."):
        return self.save(filename, directory)


    def _save_filename(self, directory, filename):
        if not filename.endswith(CC.CCDB_ZIP_SUFFIX):
            filename += CC.CCDB_ZIP_SUFFIX

        return os_path.join(directory, helpers.sanitize_path(filename))


    def yaml_version(self):
        return "1.0"


    def json_version(self):
        return "1.0"


    def to_yaml(self, root=None, show_controls=True):
        """
        Returns the string representation of the serialization of the devices into YAML.
        """
        import yaml
        import datetime

        ymodel = OrderedDict()
        if self.url():
            ymodel["url"] = self.url()
        ymodel["utc-timestamp"] = "{:%Y%m%d%H%M%S}".format(datetime.datetime.utcnow())
        ymodel["version"] = self.yaml_version()

        ydevs = OrderedDict()
        if root:
            ydevs[root.name()] = root.to_yaml()
            if show_controls:
                for d in root.buildControlsList():
                    ydevs[d.name()] = d.to_yaml()
        else:
            for (k, v) in self._devices.items():
                ydevs[k] = v.to_yaml()
        ymodel["devices"] = ydevs

        # Dump identical values verbatim and do not use anchor-alias notation
        class NoAliasDumper(yaml.Dumper):
            def ignore_aliases(self, data):
                return True

        yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data.items()))
        return yaml.dump(ymodel, sort_keys = False, Dumper = NoAliasDumper)


    def to_json(self, root=None, show_controls=True):
        """
        Returns the string representation of the serialization of the devices into JSON.
        """
        import json
        import datetime

        def special_json(cls):
            return cls.to_json()

        jmodel = OrderedDict()
        if self.url():
            jmodel["url"] = self.url()
        jmodel["utc-timestamp"] = "{:%Y%m%d%H%M%S}".format(datetime.datetime.utcnow())
        jmodel["version"] = self.json_version()
        if root:
            jdevs = OrderedDict()
            jmodel["devices"] = jdevs
            jdevs[root.name()] = root
            if show_controls:
                for d in root.buildControlsList():
                    jdevs[d.name()] = d
        else:
            jmodel["devices"] = self._devices

        return json.dumps(jmodel, indent=4, default=special_json)


    def save(self, filename, directory = "."):
        import zipfile
        if isinstance(filename, str):
            filename = self._save_filename(directory, filename)
            dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
        else:
            dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
            filename = filename.name

        # ast.literal_eval cannot parse OrderedDict so convert self._devices to simple dict()
        dumpfile.writestr(os_path.join("ccdb", CC.DEVICE_DICT), str(dict(self._devices)))
        dumpfile.writestr(os_path.join("ccdb", CC.DEVICE_JSON), self.to_json())
        try:
            dumpfile.writestr(os_path.join("ccdb", CC.DEVICE_YAML), self.to_yaml())
        except Exception:
            # Not a showstopper yet:
            #  - 'yaml' might not be installed
            #  - to_yaml() might not be correct
            pass
        for template in self._downloadedArtifacts:
            dumpfile.write(template, os_path.join("ccdb", template))

        return filename


    @staticmethod
    def open(name = None, **kwargs):
        if name is not None:
            if os_path.exists(name):
                return CC.load(name)
            elif name.endswith(CC.CCDB_ZIP_SUFFIX):
                raise CC.Exception("Cannot find " + name)

        from ccdb import CCDB
        return CCDB(name, **kwargs)


    @staticmethod
    def open_from_args(args):
        return CC.open(args.ccdb, clear_templates = args.clear_ccdb_cache)


    @staticmethod
    def load(filename):
        from ccdb_dump import CCDB_Dump
        print("Trying to load CC dump from", filename)
        return CCDB_Dump.load(filename)


    def _backtrack(self, device, prop, ex_to_raise = None):
        assert isinstance(prop, str)

        """
        ex_to_raise: Exception to raise if property is not found
        """
        deviceName = device.name()

        # starting by one device, looking for property X, find a device
        # in a higher level of the hierarchy that has that property

        if (deviceName, prop) in self._backtrackCache:
            return self._backtrackCache[deviceName, prop]

        if ex_to_raise is None:
            ex_to_raise = CC.Exception

        # starting point: all devices 'device' is controlled by
        leftToProcess = device.controlledBy(True)
        # if not controlled by anything, search device itself. Mandatory for artifacts attached to the root device itself
        if not leftToProcess:
            leftToProcess = [ device ]

        # keep track of number of iterations
        count = 0

        # process tree in BFS manner
        processed = []
        while True:

            if count > 200:
                raise CC.Exception("Something went wrong; too many iterations in backtracking while searching for property " + prop)

            if len(leftToProcess) == 0:
                raise ex_to_raise("No such backtrack property: {}".format(prop))

            elem = leftToProcess.pop()

            if elem in processed:
                continue

            processed.append(elem)

            # get properties of device
            propDict = elem.propertiesDict()

            if prop in propDict:
                val = propDict.get(prop)
                self._backtrackCache[deviceName, prop] = val

                return val

            # desired property not found in device x
            else:
                c = elem.controlledBy(True)
                if c is not None:
                    leftToProcess = c + leftToProcess
                    count        += 1


    def computeHash(self, hashobj):
        # compute checksum and hash
        # from all keys and their corresponding values in order, e.g.
        # key_1, value_1, key_2, value_2, ... key_n, value_n

        # get all devices
        deviceNames = self._devices.keys()

        # now the same for each device in alphabetical order:
        for deviceName in sorted(deviceNames):
            device = self._devices[deviceName]

            # Make sure that only controlled devices are hashed
            if not device.isInControlledTree():
                continue

            hashobj.update(deviceName)

            for k in sorted(device.keys()):
                tmp = self._getOrderedString([device[k]])

                hashobj.update(k)
                hashobj.update(tmp)


    # recursively process input in order to create an "ordered"
    # string of all properties
    @staticmethod
    def _getOrderedString(inp):
        assert isinstance(inp, list)

        res       = ""
        toProcess = list(inp)

        while not toProcess == []:

            head = toProcess.pop(0)

            if isinstance(head, str):
                res += head

            elif isinstance(head, list):
                for elem in head:
                    toProcess.append(elem)

            elif isinstance(head, dict):
                for elem in sorted(head.keys()):
                    toProcess.append(elem)
                    toProcess.append(head[elem])

            elif isinstance(head, bool):
                res += str(head)

            elif head is None:
                continue

            else:
                # Python3 does not have basestring
                try:
                    if isinstance(head, basestring):
                        res += head
                        continue
                except:
                    pass
                raise CC.Exception("Input error {}".format(type(head)))

        return res


    @staticmethod
    def tool_output_format_args(parser):
        default_json = False
        try:
            import yaml
            parser.add_argument(
                                "--yaml",
                                default = True,
                                help = "output in YAML format",
                                action = "store_true",
                                )
        except ImportError:
            default_json = True

        parser.add_argument(
                            "--json",
                            default = default_json,
                            help = "output in JSON format",
                            action = "store_true",
                            )

        return parser


    @staticmethod
    def tool_device_args(parser, device_is_required=True):
        parser.add_argument(
                        "--device",
                        help = "device to get information about",
                        required = device_is_required,
                       )


    @staticmethod
    def tool_show_subparser(subparser, device_is_required=True):
        show_parser = subparser.add_parser("show", help="Show information")
        CC.tool_device_args(show_parser, device_is_required)
        show_parser.add_argument(
                            "--no-controls-tree",
                            help = "do not include list of controlled devices",
                            dest = "no_controls_tree",
                            default = False,
                            action = "store_true",
                           )
        CC.tool_output_format_args(show_parser)

        return show_parser


    def tool_show(self, args):
        kwargs = dict()
        if args.device:
            kwargs = dict({"root": self.device(args.device), "show_controls": not args.no_controls_tree})

        if args.json:
            print(self.to_json(**kwargs))
        else:
            print(self.to_yaml(**kwargs))


    @staticmethod
    def tool_controls_tree_subparser(subparser):
        tree_parser = subparser.add_parser("controls-tree", help="Show controls tree information")
        CC.tool_device_args(tree_parser)

        return tree_parser


    def tool_controls_tree(self, args):
        device = self.device(args.device)
        device.buildControlsList(include_self = True, verbose = True)
