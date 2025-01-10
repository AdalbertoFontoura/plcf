from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: CCDB Interactions """

__author__     = "Krisztian Loki, Gregor Ulm"
__copyright__  = "Copyright 2016,2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import json
from collections import OrderedDict
from ast import literal_eval as ast_literal_eval
from platform import node 
# PLC Factory modules
from cc import CC



class CCDB(CC):
    class Artifact(CC.Artifact):
        def __init__(self, device, artifact):
            # Needs to be _before_ superclass __init__; superclass calls is_file()
            self._artifact = artifact
            super(CCDB.Artifact, self).__init__(device)


        def name(self):
            return self._artifact["name"]


        def is_file(self):
            return self._type() == "FILE"


        def is_uri(self):
            return self._type() == "URI"


        def filename(self):
            return self.name()


        def uri(self):
            return self._artifact["uri"]


        def uniqueID(self):
            if self.is_uri():
                # ignore deviceType, the URL already makes the path unique
                return ""

            if self.is_perdevtype():
                return self._device.deviceType()

            return self._device.name()


        def is_perdevtype(self):
            return self._artifact["kind"] == "TYPE"


        def _determine_saveas_url(self):
            if self.is_file():
                if self.is_perdevtype():
                    url = CCDB.urljoin("deviceTypes", self._device.deviceType(), "download", self.filename())
                else:
                    url = CCDB.urljoin("slots", self._device.name(), "download", self.filename())

                return CCDB.urljoin(self._device.ccdb.rest_url(), url)

            return super(CCDB.Artifact, self)._determine_saveas_url()


        def _download(self):
            if self.is_file():
                self._device.ccdb.download_from_ccdb(self, self.saveas())
            else:
                super(CCDB.Artifact, self)._download()


        def _type(self):
            return self._artifact["type"]



    class DeviceType(CC.DeviceType):
        def __init__(self, name, ccdb = None):
            super(CCDB.DeviceType, self).__init__(ccdb)
            self._name = name


        def __str__(self):
            return self.name()


        def __repr__(self):
            return str(self)


        def name(self):
            return self._name


        def url(self):
            return CCDB.urljoin(self.ccdb.url(), "device-types.xhtml?name={}".format(CCDB.urlquote(self.name())))



    class Device(CC.Device):
        def __init__(self, slot, ccdb = None):
            super(CCDB.Device, self).__init__(ccdb)
            self._slot  = slot
            self._devtypeprops = None
            self._props = None
            self._arts  = None


        def __repr__(self):
            return str(self._slot)


        def __getitem__(self, item):
            return self._slot[item]


        def to_yaml(self):
            """
            Returns the Python object that should be serialized into YAML
            """
            return self._slot


        def to_json(self):
            """
            Returns the Python object that should be serialized into YAML
            """
            return self._slot


        def url(self):
            return CCDB.urljoin(self.ccdb.url(), "?name={}".format(CCDB.urlquote(self.name())))


        def keys(self):
            return self._slot.keys()


        def name(self):
            return self._slot["name"]


        def type(self):
            return CCDB.DeviceType(self.deviceType(), self.ccdb)


        def _controls(self):
            return map(lambda dn: self.ccdb.device(dn), self._ensure(self._slot.get("controls", []), list))


        def _controlledBy(self, filter_by_controlled_tree):
            return filter(lambda nn: nn is not None, map(lambda dn: self.ccdb.device(dn, filter_by_controlled_tree), self._ensure(self._slot.get("controlledBy", []), list)))


        def _properties(self):
            if self._props is not None:
                return self._props

            props = self._ensure(self._slot.get("properties", []), list, False)
            self._props = OrderedDict()
            self._devtypeprops = OrderedDict()
            for prop in props:
                name  = prop.get("name")
                value = prop.get("value")

                if "List" in prop.get("dataType"):
                    if value == "null":
                        value = []
                    else:
                        value = ast_literal_eval(value)
                        assert isinstance(value, list)
                elif value == "null":
                    value = None

                # sanity check against duplicate values, which would point to an
                # issue with the entered data
                assert name not in self._props

                if prop.get("kind") == "TYPE":
                    self._devtypeprops[name] = value

                self._props[name] = value

            return self._props


        def _propertiesDict(self, prefixToIgnore = True):
            return self.ccdb._propertiesDict(self, prefixToIgnore)


        def _devtypeProperties(self):
            if self._devtypeprops is not None:
                return self._devtypeprops

            self._properties()

            return self._devtypeprops


        def _deviceType(self):
            return self._slot.get("deviceType", None)


        def _description(self):
            return self._slot.get("description", "")


        def _artifact(self, a):
            """
            Instantiates and returns an Artifact object from 'a'
            """
            return CCDB.Artifact(self, a)


        def _artifacts(self):
            if self._arts is not None:
                return self._arts

            self._arts = self._ensure(map(lambda a: self._artifact(a), self._ensure(self._slot.get("artifacts", []), list)), list)

            return self._arts


        def _backtrack(self, prop, ex_to_raise):
            return self.ccdb._backtrack(self, prop, ex_to_raise)



    @staticmethod
    def default_url():
        return "https://ccdb.esss.lu.se"


    def __init__(self, url = None, verify_ssl_cert = True, **kwargs):
        CC.__init__(self, **kwargs)
        CCDB.Device.ccdb = self

        if url is None:
            self._base_url = CCDB.default_url()
        else:
            self._base_url = url

        self._rest_url = self.urljoin(self._base_url, "rest")

        self._verify_ssl_cert = verify_ssl_cert
        self._proxies = {
            'http': 'tn-proxy-01.tn.esss.lu.se:8888',
            'https': 'tn-proxy-01.tn.esss.lu.se:8888',
        } if 'vdog-ws' in node() else None

    def url(self):
        return self._base_url


    def rest_url(self):
        return self._rest_url


    def download_from_ccdb(self, artifact_or_url, save_as):
        if isinstance(artifact_or_url, CCDB.Artifact):
            url = artifact_or_url.saveas_url()
        else:
            url = self.urljoin(self._rest_url, artifact_or_url)
        
        return CC.download(url, save_as, verify_ssl_cert = self._verify_ssl_cert, proxies=self._proxies)

    def getAllDeviceNames(self):
        url = self.urljoin(self._rest_url, "slotNames")

        result  = self._get(url)
        tmpList = filter(lambda x: x["slotType"] == "SLOT", json.loads(result.text)["names"])

        # get all devices in CCDB
        allDevices = map(lambda x: x["name"], tmpList)

        # convert unicode to String
        allDevices = map(lambda x: str(x), allDevices)

        return allDevices


    def deviceName(self, deviceName):
        """
            Handles the case when a dictionary from a controls/controlledBy/etc list is used as 'deviceName'
        """
        try:
            return deviceName["name"]
        except TypeError:
            return deviceName


    def _get_device(self, deviceName, single_device_only):
        deviceName = self.deviceName(deviceName)

        if deviceName not in self._devices:
            url = self.urljoin(self._rest_url, "slots", deviceName)

            result = self._get(url)

            if result.status_code != 200:
                raise CC.DownloadException(url = url, code = result.status_code)

            # Old versions of CCDB returned the installation slot entry itself and not a dictionary
            tmpDict = json.loads(result.text)
            try:
                device = self.tostring(tmpDict["installationSlots"])
                if not device:
                    raise CC.NoSuchDeviceException(deviceName)

                if len(device) > 1:
                    raise CC.Exception("More than one device found with the same name: {}".format(deviceName))

                device = device[0]
            except KeyError:
                device = self.tostring(tmpDict)

            # compute here so that we can add device to _devices to maintain order of devices
            need_controls = not single_device_only and not self._devices

            # save downloaded data
            self._devices[deviceName] = self.Device(device, ccdb = self)

            if need_controls:
                # If this is the first device, assume this is the root device, so
                # Greedily request transitive controls information
                url = self.urljoin(self._rest_url, "slots", deviceName, "controls/?transitive=True")

                result = self._get(url)
                if result.status_code == 200:
                    slots = self.tostring(json.loads(result.text)["installationSlots"])
                    for slot in slots:
                        self._devices[slot["name"]] = self.Device(slot, ccdb = self)

        return self._devices[deviceName]


    def _get(self, url):
        return CC.get(url, headers = { 'Accept': 'application/json' }, verify = self._verify_ssl_cert, proxies=self._proxies)

def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description = "Prints information from CCDB about device")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    def save(ccdb, args):
        ccdb.save(args.save_as)

    save_parser = subparsers.add_parser("save", help="Save a CCDB dump")
    save_parser.set_defaults(func=save)
    CC.tool_device_args(save_parser)
    save_parser.add_argument(
                        "--save-as",
                        help = "save as .zip file",
                        required = True,
                        type = str)

    def show(ccdb, args):
        ccdb.tool_show(args)

    show_parser = CC.tool_show_subparser(subparsers)
    show_parser.set_defaults(func=show)

    def controls_tree(ccdb, args):
        ccdb.tool_controls_tree(args)

    tree_parser = CC.tool_controls_tree_subparser(subparsers)
    tree_parser.set_defaults(func=controls_tree)

    CCDB.addArgs(parser)
    CC.tool_output_format_args(parser)

    args = parser.parse_args(argv)

    ccdb = CCDB.open_from_args(args)
    try:
        single_device_only = args.no_controls_tree
    except AttributeError:
        single_device_only = False
    ccdb.device(args.device, single_device_only = single_device_only)
    args.func(ccdb, args)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
