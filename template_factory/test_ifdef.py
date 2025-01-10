from __future__ import absolute_import
from __future__ import print_function


import collections
import os
import shutil
import tempfile
import unittest

import tf_ifdef


class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        if type is None:
            shutil.rmtree(self.dirpath)


class TestIF_DEF(unittest.TestCase):
    def setUp(self):
        # Clear any previous ifdef registration
        tf_ifdef.PV.init(None)


    def tearDown(self):
        pass


    def test_pv_name(self):
        with mkdtemp(prefix = "test-ifdef-pvname") as tmpdir:
            pv_name_def = os.path.join(tmpdir, "pvname.def")
            with open(pv_name_def, "w") as def_file:
                print("""
define_status_block()

add_digital("both")
add_digital("plc", PV_NAME="epics")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(pv_name_def, QUIET = True)

            var = ifdef.has_pv("both")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "both")
            self.assertEqual(var.name(), "both")
            self.assertEqual(var.fqpn(), "INST:SLOT:both")
            self.assertEqual(len(var._pv_fields), 0)

            var = ifdef.has_pv("plc")
            self.assertIsNone(var)

            var = ifdef.has_pv("epics")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "epics")
            self.assertEqual(var.name(), "plc")
            self.assertEqual(var.fqpn(), "INST:SLOT:epics")
            self.assertEqual(len(var._pv_fields), 0)

            # Check that IF_DEF.parse() properly closed the creation
            #  and PV no longer has a link to an ifdef
            with self.assertRaises(tf_ifdef.IfDefInternalError):
                tf_ifdef.PV.create_fqpn("foo")

            # Check that IF_DEF.parse() properly closed the creation
            #  and PV no longer has a link to an ifdef
            with self.assertRaises(tf_ifdef.IfDefInternalError):
                tf_ifdef.PV.create_root_fqpn("foo")

        with tf_ifdef.IF_DEF(QUIET = True) as ifdef:

            ifdef.define_status_block()
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                ifdef.add_digital("foo", PV_NAME="bar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
            bar = ifdef.add_digital("foo", PV_NAME="$(bar)-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")._var
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                bar.fqpn("foobar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                bar.fqpn("foobar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write.DESC")
            bar.fqpn("foobar.and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")


    def test_pv_duplication(self):
        with tf_ifdef.IF_DEF(QUIET = True) as ifdef:

            foo = tf_ifdef.PV("", "foo", "bo")

            with self.assertRaises(tf_ifdef.IfDefSyntaxError) as exp:
                tf_ifdef.PV("", "foo", "ao")
            exp = exp.exception
            self.assertEqual(exp.args[0], "PV Names must be unique")

            ifdef.define_parameter_block()
            ifdef.add_analog("pfoo", "INT", PV_NAME="analog_foo")

            with self.assertRaises(tf_ifdef.IfDefSyntaxError) as exp:
                ifdef.add_digital("pfoo", PV_NAME="digital_foo")
            exp = exp.exception
            self.assertEqual(exp.args[0], "PLC variable names must be unique")

        self.assertIsInstance(ifdef.has_pv("foo"), tf_ifdef.PV)
        self.assertIsInstance(ifdef.has_pv("analog_foo"), tf_ifdef.ANALOG)


    def test_pv_duplication_plc_footer(self):
        with tf_ifdef.IF_DEF(QUIET = True, PLCF = tf_ifdef.ROOT_IF_DEF.create_dummy_plcf()) as ifdef:
            tf_ifdef.PV("", tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV, "bo")

        with self.assertRaises(tf_ifdef.IfDefSyntaxError) as exp:
            with tf_ifdef.FOOTER_IF_DEF(None, [ifdef]) as footer_ifdef:
                pass
        exp = exp.exception
        self.assertEqual(exp.args[0], "PV Names must be unique")


    def test_alias(self):
        with mkdtemp(prefix = "test-ifdef-alias") as tmpdir:
            alias_def = os.path.join(tmpdir, "alias.def")
            with open(alias_def, "w") as def_file:
                print("""
define_status_block()

add_digital("no-alias")
add_digital("foo", PV_ALIAS="bar")
add_digital("foo2", PV_ALIAS=["bar2", "foobar2"])
add_digital("short", PV_ALIAS="an-alias-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alias_def, QUIET = True)

            var = ifdef.has_pv("no-alias")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "no-alias")
            self.assertEqual(var.fqpn(), "INST:SLOT:no-alias")
            self.assertEqual(var.name(), "no-alias")
            self.assertEqual(var._pv_aliases, [])
            self.assertEqual(var.build_pv_alias(), "")

            var = ifdef.has_pv("foo")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "foo")
            self.assertEqual(var.fqpn(), "INST:SLOT:foo")
            self.assertEqual(var.name(), "foo")
            self.assertEqual(var._pv_aliases, ["bar"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar")
""")

            var = ifdef.has_pv("foo2")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "foo2")
            self.assertEqual(var.fqpn(), "INST:SLOT:foo2")
            self.assertEqual(var.name(), "foo2")
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
""")
            var.add_alias("plus")
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2", "plus"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
\talias("INST:SLOT:plus")
""")
            var.add_alias(["left", "right"])
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2", "plus", "left", "right"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
\talias("INST:SLOT:plus")
\talias("INST:SLOT:left")
\talias("INST:SLOT:right")
""")

            var = ifdef.has_pv("short")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "short")
            self.assertEqual(var.fqpn(), "INST:SLOT:short")
            self.assertEqual(var.name(), "short")
            self.assertEqual(var._pv_aliases, ["an-alias-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write"])
            self.assertGreater(len(var._pv_aliases[0]), 60)
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                var.build_pv_alias()


    def test_fields(self):
        with mkdtemp(prefix = "test-ifdef-fields") as tmpdir:
            field_def = os.path.join(tmpdir, "field.def")
            with open(field_def, "w") as def_file:
                print("""
define_status_block()

add_digital("no-field")
add_digital("desc", PV_DESC="description")
add_digital("long-desc", PV_DESC="this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be")
add_digital("moar-fields", PV_DESC="desc", PV_HIGH="0")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(field_def, QUIET = True)

            var = ifdef.has_pv("no-field")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "no-field")
            self.assertEqual(len(var._pv_fields), 0)
            self.assertNotIsInstance(var._pv_fields, collections.OrderedDict)
            self.assertEqual(var.build_pv_extra(), "")

            var = ifdef.has_pv("desc")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "desc")
            self.assertEqual(var.get_pv_field("DESC"), "description")
            self.assertEqual(var.get_pv_field(tf_ifdef.PV.PV_DESC), "description")
            self.assertEqual(len(var._pv_fields), 1)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "description")""")

            var = ifdef.has_pv("long-desc")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "long-desc")
            self.assertGreater(len(var.get_parameter(tf_ifdef.PV.PV_DESC)), 40)
            self.assertEqual(len(var.get_pv_field("DESC")), 40)
            self.assertEqual(var.get_pv_field("DESC"), "this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be"[:40])
            self.assertEqual(len(var._pv_fields), 1)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "{}")""".format("this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be"[:40]))

            var = ifdef.has_pv("moar-fields")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(len(var._pv_fields), 2)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "desc")
\tfield(HIGH, "0")""")
            var.set_pv_field("ZNA", "znam")
            self.assertEqual(len(var._pv_fields), 3)
            self.assertEqual(var.get_pv_field("ZNA"), "znam")
            var.set_pv_field(tf_ifdef.PV.PV_ONAM, "onam")
            self.assertEqual(len(var._pv_fields), 4)
            self.assertEqual(var.get_pv_field("ONAM"), "onam")
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "desc")
\tfield(HIGH, "0")
\tfield(ONAM, "onam")
\tfield(ZNA,  "znam")""")


    def test_add_alarm_limits(self):
        with mkdtemp(prefix = "test-ifdef-add-alarm-limits") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
add_minor_low_limit("milow")
add_major_low_limit("malow")
add_minor_high_limit("mihigh", "REAL")
add_major_high_limit("mahigh", "INT")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            meas = ifdef.has_pv("meas")
            self.assertIsInstance(meas, tf_ifdef.ANALOG)
            self.assertEqual(meas.plc_type(), "REAL")
            self.assertEqual(meas.get_pv_field("LSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("LLSV"), "MAJOR")
            self.assertEqual(meas.get_pv_field("HSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("HHSV"), "MAJOR")
            self.assertEqual(meas.build_pv_extra(), """
\tfield(HHSV, "MAJOR")
\tfield(HSV,  "MINOR")
\tfield(LLSV, "MAJOR")
\tfield(LSV,  "MINOR")""")

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            var = ifdef.has_pv("milow")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#milow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            check_common_limit(ivar)

            var = ifdef.has_pv("malow")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#malow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOLO")
            check_common_limit(ivar)

            var = ifdef.has_pv("mihigh")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#mihigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIGH")
            check_common_limit(ivar)

            var = ifdef.has_pv("mahigh")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "INT")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#mahigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            check_common_limit(ivar)


    def test_set_alarm_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-alarm-limits-from") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
set_minor_low_limit_from("milow")
set_major_low_limit_from("malow", EXTERNAL_PV = True)
set_minor_high_limit_from("mihigh")
set_major_high_limit_from("ext:mahigh")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            meas = ifdef.has_pv("meas")
            self.assertIsInstance(meas, tf_ifdef.ANALOG)
            self.assertEqual(meas.plc_type(), "REAL")
            self.assertEqual(meas.get_pv_field("LSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("LLSV"), "MAJOR")
            self.assertEqual(meas.get_pv_field("HSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("HHSV"), "MAJOR")
            self.assertEqual(meas.build_pv_extra(), """
\tfield(HHSV, "MAJOR")
\tfield(HSV,  "MINOR")
\tfield(LLSV, "MAJOR")
\tfield(LSV,  "MINOR")""")

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            ivar = ifdef.has_pv("#milow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:milow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#malow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "malow CP")
            self.assertEqual(ivar.get_parameter("PV_DOL"), "malow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOLO")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#mihigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:mihigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIGH")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#mahigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "ext:mahigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            check_common_limit(ivar)


    def test_set_multiple_alarm_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-multiple-alarm-limits-from") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
set_minor_low_limit_from("limit")
set_major_high_limit_from("limit2")

add_analog("meas2", "INT")
#set_minor_high_limit_from("")
set_major_high_limit_from("limit2")
set_major_low_limit_from("limit")

add_analog("meas3", "WORD")
set_minor_high_limit_from("limit")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            def check_limited(name, typ, field, sevr, field_num):
                meas = ifdef.has_pv(name)
                self.assertIsInstance(meas, tf_ifdef.ANALOG)
                self.assertEqual(meas.plc_type(), typ)
                self.assertEqual(meas.get_pv_field(field), sevr)
                self.assertEqual(len(meas._pv_fields), field_num)

            check_limited("meas", "REAL", "LSV", "MINOR", 2)
            check_limited("meas", "REAL", "HHSV", "MAJOR", 2)
            check_limited("meas2", "INT", "LLSV", "MAJOR", 2)
            check_limited("meas2", "INT", "HHSV", "MAJOR", 2)
            check_limited("meas3", "WORD", "HSV", "MINOR", 1)

            limit = ifdef.has_pv("#limit")
            self.assertIsInstance(limit, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(limit.get_pv_field("DOL"), "INST:SLOT:limit CP")
            self.assertEqual(limit.get_pv_field("OMSL"), "closed_loop")
            self.assertEqual(limit.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            self.assertEqual(limit.get_pv_field("OUTB"), "INST:SLOT:meas2.LOLO")
            self.assertEqual(limit.get_pv_field("OUTC"), "INST:SLOT:meas3.HIGH")
            self.assertTrue(limit.get_pv_field("DESC"))
            self.assertEqual(len(limit._pv_fields), 6)

            limit = ifdef.has_pv("#limit2")
            self.assertIsInstance(limit, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(limit.get_pv_field("DOL"), "INST:SLOT:limit2 CP")
            self.assertEqual(limit.get_pv_field("OMSL"), "closed_loop")
            self.assertEqual(limit.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            self.assertEqual(limit.get_pv_field("OUTB"), "INST:SLOT:meas2.HIHI")
            self.assertTrue(limit.get_pv_field("DESC"))
            self.assertEqual(len(limit._pv_fields), 5)


    def test_set_drive_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-drive-limits-from") as tmpdir:
            drive_def = os.path.join(tmpdir, "drive.def")
            with open(drive_def, "w") as def_file:
                print("""
define_parameter_block()

add_analog("param", "REAL")
set_low_drive_limit_from("dlow")
set_high_drive_limit_from("ext:dhigh")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(drive_def, QUIET = True)

            param = ifdef.has_pv("param")
            self.assertIsInstance(param, tf_ifdef.ANALOG)
            self.assertEqual(param.plc_type(), "REAL")
            self.assertEqual(len(param._pv_fields), 0)

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            ivar = ifdef.has_pv("#dlow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:dlow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.LOPR")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#dhigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "ext:dhigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.HOPR")
            check_common_limit(ivar)


    def test_set_multiple_drive_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-multiple-drive-limits-from") as tmpdir:
            drive_def = os.path.join(tmpdir, "drive.def")
            with open(drive_def, "w") as def_file:
                print("""
define_parameter_block()

add_analog("param", "REAL")
set_low_drive_limit_from("dlow")

add_analog("param1", "INT")
set_low_drive_limit_from("dlow")

add_analog("param2", "WORD")
set_high_drive_limit_from("dlow")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(drive_def, QUIET = True)

            def check_driven(var, typ, limits):
                self.assertIsInstance(var, tf_ifdef.ANALOG)
                self.assertEqual(var.plc_type(), typ)
                if limits:
                    self.assertEqual(set(var._pv_fields.keys()), set(["PV_DRVL", "PV_DRVH", "PV_LOPR", "PV_HOPR"]))
                else:
                    self.assertEqual(len(var._pv_fields), 0)

            param = ifdef.has_pv("param")
            check_driven(param, "REAL", False)

            param = ifdef.has_pv("param1")
            check_driven(param, "INT", True)

            param = ifdef.has_pv("param2")
            check_driven(param, "WORD", True)

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 6)

            ivar = ifdef.has_pv("#dlow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:dlow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.LOPR")
            self.assertEqual(ivar.get_pv_field("OUTB"), "INST:SLOT:param1.LOPR")
            self.assertEqual(ivar.get_pv_field("OUTC"), "INST:SLOT:param2.HOPR")
            check_common_limit(ivar)


    def test_no_parameters(self):
        with tf_ifdef.IF_DEF(QUIET = True) as ifdef:
            pass

        self.assertIsNone(ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV))
        self.assertEqual(len(ifdef._pv_names), 0)

        footer_ifdef = tf_ifdef.FOOTER_IF_DEF(None, [ifdef])

        upc = footer_ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV)
        self.assertIsInstance(upc, tf_ifdef.PARAMETER_UPLOAD_FO)
        self.assertTrue(upc.get_pv_field("DESC"))
        self.assertEqual(upc.get_pv_field("SHFT"), "0")
        self.assertEqual(upc.get_pv_field("LNK0"), "ROOT-INST:SLOT:#plcfInitUploadStat")
        self.assertEqual(upc.get_pv_field("LNK1"), "ROOT-INST:SLOT:#plcfDoneUploadStat")
        self.assertEqual(len(upc._pv_fields), 4)

        self.assertIsInstance(footer_ifdef.has_pv("#plcfInitUploadStat"), tf_ifdef.PV)
        self.assertIsInstance(footer_ifdef.has_pv("#plcfDoneUploadStat"), tf_ifdef.PV)
        self.assertIsInstance(footer_ifdef.has_pv("#plcfAssertUplStat"), tf_ifdef.PV)

        self.assertEqual(len(footer_ifdef._pv_names), 4)


    def test_parameters(self):
        with mkdtemp(prefix = "test-ifdef-parameters") as tmpdir:
            param_def = os.path.join(tmpdir, "param.def")
            with open(param_def, "w") as def_file:
                print("""
define_parameter_block()

add_digital("p1")
add_digital("p2")
add_digital("p3")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(param_def, QUIET = True)

            params = ["p1", "p2", "p3"]
            for param in params:
                pv = ifdef.has_pv(param)
                self.assertIsInstance(pv, tf_ifdef.BIT)
                self.assertIsNone(pv.get_pv_field("FLNK"))

            dupc = ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV)
            self.assertIsInstance(dupc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(dupc.get_pv_field("DESC"))
            self.assertEqual(dupc.get_pv_field("SHFT"), "0")
            self.assertEqual(dupc.get_pv_field("LNK0"), "ROOT-INST:SLOT:HeartbeatToPLCS")
            self.assertEqual(dupc.get_pv_field("LNK1"), "INST:SLOT:p1")
            self.assertEqual(dupc.get_pv_field("LNK2"), "INST:SLOT:p2")
            self.assertEqual(dupc.get_pv_field("LNK3"), "INST:SLOT:p3")
            self.assertEqual(len(dupc._pv_fields), 6)

            self.assertEqual(len(ifdef._pv_names), 4)

            footer_ifdef = tf_ifdef.FOOTER_IF_DEF(None, [ifdef])

            upc = footer_ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV)
            self.assertIsInstance(upc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(upc.get_pv_field("DESC"))
            self.assertEqual(upc.get_pv_field("SHFT"), "0")
            self.assertEqual(upc.get_pv_field("LNK0"), "ROOT-INST:SLOT:#plcfInitUploadStat")
            self.assertEqual(upc.get_pv_field("LNK1"), dupc.fqpn())
            self.assertEqual(len(upc._pv_fields), 4)

            for param in params[:-1]:
                pv = ifdef.has_pv(param)
                self.assertIsInstance(pv, tf_ifdef.BIT)
                self.assertIsNone(pv.get_pv_field("FLNK"))

            self.assertEqual(ifdef.has_pv(params[-1]).get_pv_field("FLNK"), "ROOT-INST:SLOT:#plcfDoneUploadStat")

            self.assertIsInstance(footer_ifdef.has_pv("#plcfInitUploadStat"), tf_ifdef.PV)
            self.assertIsInstance(footer_ifdef.has_pv("#plcfDoneUploadStat"), tf_ifdef.PV)
            self.assertIsInstance(footer_ifdef.has_pv("#plcfAssertUplStat"), tf_ifdef.PV)

            self.assertEqual(len(footer_ifdef._pv_names), 4)


    def test_last_parameter_with_flnk(self):
        with mkdtemp(prefix = "test-ifdef-last-parameter-with-flnk") as tmpdir:
            param_def = os.path.join(tmpdir, "param.def")
            with open(param_def, "w") as def_file:
                print("""
define_parameter_block()

add_digital("p", PV_FLNK="foo:bar")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(param_def, QUIET = True)

            param = ifdef.has_pv("p")
            self.assertIsInstance(param, tf_ifdef.BIT)
            self.assertEqual(param.get_pv_field("FLNK"), "foo:bar")

            dupc = ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV)
            self.assertIsInstance(dupc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(dupc.get_pv_field("DESC"))
            self.assertEqual(dupc.get_pv_field("SHFT"), "0")
            self.assertEqual(dupc.get_pv_field("LNK0"), "ROOT-INST:SLOT:HeartbeatToPLCS")
            self.assertEqual(dupc.get_pv_field("LNK1"), "INST:SLOT:p")
            self.assertEqual(len(dupc._pv_fields), 4)

            self.assertEqual(len(ifdef._pv_names), 2)

            footer_ifdef = tf_ifdef.FOOTER_IF_DEF(None, [ifdef])

            upc = footer_ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV)
            self.assertIsInstance(upc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(upc.get_pv_field("DESC"))
            self.assertEqual(upc.get_pv_field("SHFT"), "0")
            self.assertEqual(upc.get_pv_field("LNK0"), "ROOT-INST:SLOT:#plcfInitUploadStat")
            self.assertEqual(upc.get_pv_field("LNK1"), dupc.fqpn())
            self.assertEqual(len(upc._pv_fields), 4)

            helper = footer_ifdef.has_pv("#plcfLastPrmHlper-FO")
            self.assertIsInstance(helper, tf_ifdef.PV)
            self.assertTrue(helper.get_pv_field("DESC"))
            self.assertEqual(helper.get_pv_field("LNK1"), "foo:bar")
            self.assertEqual(helper.get_pv_field("FLNK"), "ROOT-INST:SLOT:#plcfDoneUploadStat")
            self.assertEqual(len(helper._pv_fields), 3)

            self.assertEqual(param.get_pv_field("FLNK"), "ROOT-INST:SLOT:#plcfLastPrmHlper-FO")


    def test_many_parameters(self):
        with mkdtemp(prefix = "test-ifdef-many-parameters") as tmpdir:
            param_def = os.path.join(tmpdir, "param.def")
            with open(param_def, "w") as def_file:
                print("""
define_parameter_block()

add_digital("p1")
add_digital("p2")
add_digital("p3")
add_digital("p4")
add_digital("p5")
add_digital("p6")
add_digital("p7")
add_digital("p8")
add_digital("p9")
add_digital("pA")
add_digital("pB")
add_digital("pC")
add_digital("pD")
add_digital("pE")
add_digital("pF")

add_digital("q1")
add_digital("q2")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(param_def, QUIET = True)

            params = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "pA", "pB", "pC", "pD", "pE", "pF", "q1", "q2"]
            for pv in params:
                self.assertIsInstance(ifdef.has_pv(pv), tf_ifdef.BIT)

            dupc = ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV)
            self.assertIsInstance(dupc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(dupc.get_pv_field("DESC"))
            self.assertEqual(dupc.get_pv_field("SHFT"), "0")
            self.assertEqual(dupc.get_pv_field("LNK0"), "ROOT-INST:SLOT:HeartbeatToPLCS")
            self.assertEqual(dupc.get_pv_field("LNK1"), "INST:SLOT:p1")
            self.assertEqual(dupc.get_pv_field("LNK2"), "INST:SLOT:p2")
            self.assertEqual(dupc.get_pv_field("LNK3"), "INST:SLOT:p3")
            self.assertEqual(dupc.get_pv_field("LNK4"), "INST:SLOT:p4")
            self.assertEqual(dupc.get_pv_field("LNK5"), "INST:SLOT:p5")
            self.assertEqual(dupc.get_pv_field("LNK6"), "INST:SLOT:p6")
            self.assertEqual(dupc.get_pv_field("LNK7"), "INST:SLOT:p7")
            self.assertEqual(dupc.get_pv_field("LNK8"), "INST:SLOT:p8")
            self.assertEqual(dupc.get_pv_field("LNK9"), "INST:SLOT:p9")
            self.assertEqual(dupc.get_pv_field("LNKA"), "INST:SLOT:pA")
            self.assertEqual(dupc.get_pv_field("LNKB"), "INST:SLOT:pB")
            self.assertEqual(dupc.get_pv_field("LNKC"), "INST:SLOT:pC")
            self.assertEqual(dupc.get_pv_field("LNKD"), "INST:SLOT:pD")
            self.assertEqual(dupc.get_pv_field("LNKE"), "INST:SLOT:pE")
            self.assertEqual(dupc.get_pv_field("LNKF"), "INST:SLOT:pF")
            self.assertEqual(len(dupc._pv_fields), 19)

            dupc1 = ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.DEVICE_FO_PV.format(1))
            self.assertIsInstance(dupc1, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(dupc1.get_pv_field("DESC"))
            self.assertEqual(dupc1.get_pv_field("SHFT"), "0")
            self.assertEqual(dupc1.get_pv_field("LNK0"), "ROOT-INST:SLOT:HeartbeatToPLCS")
            self.assertEqual(dupc1.get_pv_field("LNK1"), "INST:SLOT:q1")
            self.assertEqual(dupc1.get_pv_field("LNK2"), "INST:SLOT:q2")
            self.assertEqual(len(dupc1._pv_fields), 5)

            self.assertEqual(dupc.get_pv_field("FLNK"), dupc1.fqpn())

            self.assertEqual(len(ifdef._pv_names), 19)

            with tf_ifdef.IF_DEF(QUIET = True, PLCF = tf_ifdef.DummyPLCF({ "[PLCF#{}]".format(tf_ifdef.IF_DEF.DEFAULT_INSTALLATION_SLOT) : "INST:SLOT2", "[PLCF#ROOT_INSTALLATION_SLOT]" : "ROOT-INST:SLOT" })) as extra_ifdef:
                extra_ifdef.define_parameter_block()
                extra_ifdef.add_digital("foo")

            # `extra_ifdef` comes first then comes `ifdef`
            footer_ifdef = tf_ifdef.FOOTER_IF_DEF(None, [extra_ifdef, ifdef])

            upc = footer_ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV)
            self.assertIsInstance(upc, tf_ifdef.PARAMETER_UPLOAD_FO)
            self.assertTrue(upc.get_pv_field("DESC"))
            self.assertEqual(upc.get_pv_field("SHFT"), "0")
            self.assertEqual(upc.get_pv_field("LNK0"), "ROOT-INST:SLOT:#plcfInitUploadStat")
            self.assertEqual(upc.get_pv_field("LNK1"), extra_ifdef.has_pv(tf_ifdef.PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV).fqpn())
            self.assertEqual(upc.get_pv_field("LNK2"), dupc.fqpn())
            self.assertEqual(len(upc._pv_fields), 5)

            self.assertIsInstance(footer_ifdef.has_pv("#plcfInitUploadStat"), tf_ifdef.PV)
            self.assertIsInstance(footer_ifdef.has_pv("#plcfDoneUploadStat"), tf_ifdef.PV)
            self.assertIsInstance(footer_ifdef.has_pv("#plcfAssertUplStat"), tf_ifdef.PV)

            self.assertEqual(len(footer_ifdef._pv_names), 4)

            self.assertIsNone(extra_ifdef.has_pv("foo").get_pv_field("FLNK"))
            self.assertEqual(ifdef.has_pv(params[-1]).get_pv_field("FLNK"), "ROOT-INST:SLOT:#plcfDoneUploadStat")



if __name__ == "__main__":
    unittest.main()

