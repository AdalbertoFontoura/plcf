Integrating PLCs into an EPICS control system can be an error-prone task. Some of the error inducing difficulties can be mitigated by using CCDB and PLC Factory to create an EPICS database, an EEE module, and PLC code that handles the communication with an IOC. Of course this does not come for free; the interface between EPICS and the PLC has to be defined somehow. This somehow is the so-called **Interface Definition**. An interface definition is a text file (technically a python script with a very limited set of functionality) that defines what kind of information travels in which direction.

# The basics of an EPICS-PLC interface

The information flow has to directions:

*   from the PLC to EPICS; sent periodically (regardless of any value-change) as a block of data  

    *   **_[status information](#status-information)_**

*   from EPICS to the PLC; sent only when requested and sent as individual data elements  

    *   **_[commands](#commands)_**
    *   **_[parameters](#parameters)_**
    *   **_[general inputs](#general-inputs)_**

## Status information

Typically these are sensor readings and various state information about the PLC program itself. A word array is constructed at the PLC side that is sent periodically and is disassembled by the IOC into individual PVs.
Status information is enclosed in a **[status block](#status-block)**.

## Commands

These are instructions to the PLC program. The PLC code resets every command to the default 0 value upon receiving. This prevents the repetition of the same command and ensures that only commands that are actually resent are interpreted as new instructions. Usually commands are one-bit values, but there is no restriction on their type.
Commands are enclosed in a **[command block](#command-block)**.

## Parameters

These are control values sent to the PLC program. Their values are preserved between PLC cycles and autosaved on the IOC side. Typical parameters are setpoints and alarm limits.
Parameters are enclosed in a **[parameter block](#parameter-block)**.

## General Inputs

These are general input / control values sent to the PLC program. Their values are preserved between PLC cycles **BUT not autosaved** on the IOC side. Typical general inputs are measurement values.
General inputs are enclosed in a **[general input block](#general-input-block)**


## Types

The following types can be used to add a variable to an interface definition:

*   **[digital](#digital-variable)**; a simple 1-bit information. Maps to the **_binary input/output_** record in EPICS and to the **_BOOL_** type in the PLC
*   **[analog](#analog-variable)**; an integer or floating point value. Maps to the **_analog input/output_** record in EPICS and the **_user specified_** PLC type in the PLC
*   **[time](#time-variable)**; an interval (NOT a timestamp) in milliseconds. Maps to the **_analog input/output_** record in EPICS and to the **_TIME_** type in the PLC
*   **[alarm](#alarm-variable)**; a simple 1-bit information that can generate an EPICS alarm. By default a value of 1 results in an alarm. Maps to the **_binary input_** record in EPICS and to the **_BOOL_** type in the PLC.
*   **[enum](#enum-variable)**; an enumeration. Maps to the **_multi-bit binary input/output_** record in EPICS and the **_user specified_** PLC type in the PLC
*   **[bitmask](#bitmask-variable)**; bits of a 16 bit integer. Maps to the **_multi-bit binary input/output direct_** record in EPICS and to the **_INT_** type in the PLC
*   **[string](#string-variable)**; a maximum 39 character long string. Maps to the **_stringin_** record in EPICS and to the **_STRING_** type in the PLC

## PLC Types

The following PLC types can be used to "back" the variables defined in the interface definition:

*   **BOOL**; it is implicitly specified with the **digital** type
*   **BYTE**; 8-bit integer
*   **USINT**; 8-bit unsigned integer
*   **SINT;** 8-bit signed integer
*   **WORD**; 16-bit unsigned integer
*   **INT**; 16-bit signed integer
*   **UINT**; 16-bit unsigned integer
*   **DWORD**; 32-bit unsigned integer
*   **DINT**; 32-bit signed integer
*   **UDINT**; 32-bit unsigned integer
*   **REAL**; 32-bit floating point number
*   **TIME**; it is implicitly specified with the **time** type
*   **STRING**; it is implicitly specified with the **string** type

## Data Layout

All the variables in each direction are assembled into a WORD (16-bit integer) array on the PLC side (the command, parameter, and general inputs blocks are concatenated to form one array). The array is filled from top to bottom, meaning that the earlier a variable shows up in the interface definition, the lower its array index will be.

Digital types are packed into WORDs so no space is wasted. The earlier the digital variable shows up, the lower its significance will be in the resulting WORD (ie. the first digital is mapped to 2⁰, the second to 2¹, and so on). If for whatever reason you need to have more control over the mapping to individual bits, spare digitals can be introduced.

**There is no mechanism to put a variable to a specific index (or bit) in the resulting array.**

# Interface Definition syntax

## General rules

Because in the current implementation every interface definition is a special subset of python the same set of rules apply as to a python script. Basically every "instruction" is a function call; thus parenthesis are mandatory. Optional arguments are represented as keyword arguments and take the form of **`KEYWORD="value"`**.

## Defining the device name A.K.A. installation slot (a CCDB-term)

While it is neither necessary nor recommended to override the default device name (retreived from CCDB by PLCFactory) it is still possible to do so. One use case is the Vacuum Mobile Pumping Kart project; it consists of about a dozen karts with completely identical PLCs (hardware and software wise). Overriding the device name enables the reuse of a base MobilePumpingKart module; just use a macro like `$(VMPG_INSTANCE)`.
This feature should be used with caution: if there are more than one devices with the same Interface Definition then the same device name will be used for all of them - that is why if the specified device name is not a macro (does not begin with a '$' sign) then it is automatically treated as a CCDB property.

**`define_installation_slot("<device_name>")`**

## Defining blocks

A block can only be defined once, empty blocks need not be defined. The scope of a block definition ends with the definition of another block.

### Status block

**`define_status_block()`**

### Command block

**`define_command_block()`**

### Parameter block

**`define_parameter_block()`**

### General input block

**`define_general_input_block()`**

## Adding variables to a block

After a block is defined it can be populated with variables. Adding a variable is done with the **`add__<type>_()`** construct. Every variable has a name; this name can be used to reference the variable in the PLC code and will be used (as the signal part) to construct the record name. Every variable has an associated PLC type, some variables (digital, time, alarm) have fixed types, for the others the type must be explicitly defined. EPICS fields can be specified with the **`PV__<field>_="value"`** keyword arguments. For example to have a different variable name in EPICS than in the PLC, the **`PV_NAME="different_name"`** argument can be used. A mockup variable declaration looks like this:

**`add_<type>("<name>", "<plc_type>" [,KEYWORD1="value"[, KEYWORD2="value"]...])`**

### Digital variable

**`add_digital("<name>")`**

**NOTE**:\
adding spare bits is deprecated and should not be used. It was introduced to support an old workflow.

Adding a spare bit:

**`add_digital()`**

**`skip_digital()`**

Adding more than one spare bit:

**`skip_digitals(<number>)`**

### Analog variable

**`add_analog("<name>", "<plc_type>")`**

#### Analog variable alarm limits

Only allowed in a **STATUS** block.

It is possible to specify alarm limits for **analog status** variables and when the value of that variable is out of a limit EPICS will automatically put the PV into the relevant alarm state. There are 4 possible limits:
1. Major low limit: **`set_major_low_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `LOLO` / `LLSV`
2. Minor low limit: **`set_minor_low_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `LOW` / `LSV`
3. Minor high limit: **`set_minor_high_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `HIGH` / `HSV`
4. Major high limit: **`set_major_high_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `HIHI` / `HHSV`

The limits are enforced on the **previously specified** _analog_ variable (the _limited_ variable); in other words first you define an analog variable with `add_analog()` then **right after** this variable you define the alarm limits. Any number of limits can be defined (though you shouldn't specify more than 4 ;) ). _Major low_ should be less then _minor low_ and _major high_ should be greater than _minor high_.

`"<name>"` is assumed to have the same device name / ESS name as the _limited_ variable unless it contains a `:` or `EXTERNAL_PV` is True

This sets one of the _HIHI_,_HIGH_,_LOLO_,_LOW_ fields of the _limited_ variable whenever the value of the limit record changes. The same limit can be applied to at most 8 variables.


There is a shortcut to create the limiting variable and register it as a limit in one line:
1. Major low limit: **`add_major_low_limit("<name>", ["<plc_type>"])`**
2. Minor low limit: **`add_minor_low_limit("<name>", ["<plc_type>"])`**
3. Minor high limit: **`add_minor_high_limit("<name>", ["<plc_type>"])`**
4. Major high limit: **`add_major_high_limit("<name>", ["<plc_type>"])`**

This is the same as `add_analog("foo", "REAL")` followed by a `set_.._limit_from("foo")`

If `<plc_type>` is omitted it is taken from the _limited analog_ variable.


[Examples](#alarm-limit-examples)

#### Analog variable drive limits

Only allowed in **COMMAND**, **PARAMETER**, or **GENERAL INPUT** blocks.

It is possible to specify **OPI** drive limits (`LOPR` and `HOPR`) for **analog command / parameter / general input** variables meaning that the OPI control widget's input range will be set to these limits. Whenever the value of limit changes the limit will be updated in the _limited_ analog variable. There are 2 possible limits:
1. Low drive limit: **`set_low_drive_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `LOPR`
2. High drive limit: **`set_high_drive_limit_from("<name>"[, EXTERNAL_PV=True])`**
    *   Sets `HOPR`

The limits are enforced on the **previously specified** _analog_ variable (the _limited_ variable); in other words first you define an analog variable with `add_analog()` then **right after** this variable you define the drive limits. Although it is not enforced by PLCFactory you should set both limits (either with `set_*_drive_limit_from` or `PV_HOPR`/`PV_LOPR` keywords); Phoebus might get confused if only one limit is set.

`"<name>"` is assumed to have the same device name / ESS name as the _limited_ variable unless it contains a `:` or `EXTERNAL_PV` is True

This sets one of the _LOPR_,_HOPR_ fields of the _limited_ variable whenever the value of the limit record changes. The same limit can be applied to at most 8 variables.


[Examples](#drive-limit-examples)

### Time variable

**`add_time("<name>")`**

### Alarm variable

Only allowed in a **STATUS** block

Creates a **BOOL** PLC variable and a **bi** EPICS record and sets the appropriate alarm state based on the value of the PV.

A MINOR alarm if the value is 1:

**`add_minor_alarm("<name>", "<short_alarm_message>")`**

A MAJOR alarm if the value is 1:

**`add_major_alarm("<name>", "<short_alarm_message>")`**

A MINOR alarm if the value is 0:

**`add_minor_alarm("<name>", "<short_alarm_message>", ALARM_IF=False)`**

A MAJOR alarm if the value is 0:

**`add_major_alarm("<name>", "<short_alarm_message>", ALARM_IF=False)`**

The _`short_alarm_message`_ will end up in the PV's ONAM (or ZNAM) field

### Enum variable

Creates a PLC variable of type **<plc_type>** and an **mbbi** or **mbbo** EPICS record

**`add_enum("<name>", "<plc_type">)`**

### Bitmask variable

Creates a PLC variable of type **<plc_type>** and an **mbbiDirect** or **mbboDirect** EPICS record

**`add_bitmask("<name>", "<plc_type">)`**

### String variable

**`add_string("<name>" [, length])`**

The default length is the maximum allowed by EPICS; 39 characters

## Customizing / adding new PVs to the generated EPICS db

If for some reason you have to add custom PVs whose values are not coming from the PLC you can use the `add_verbatim` function. It will copy everthing verbatim (subject to PLCF# evaluation).

```
add_verbatim("""
record(calcout, "[PLCF#INSTALLATION_SLOT]:#CalcFbkError")
{
    field(DESC, "Aggregate feedback errors")
    field(INPA, "[PLCF#INSTALLATION_SLOT]:ISrcMagPS_fbkErrorC1 CP MSS")
    field(INPB, "[PLCF#INSTALLATION_SLOT]:ISrcMagPS_fbkErrorC2 CP MSS")
    field(CALC, "A && B")
    field(OUT,  "[PLCF#INSTALLATION_SLOT]:FbkError PP MSS")
    field(SCAN, "1 second")
}


record(bi, "[PLCF#INSTALLATION_SLOT]:FbkError")
{
    field(DESC, "If there is a feedback error")
    field(ZNAM, "Feedback error")
    field(ONAM, "Good")
}
""")
```

will substitute `[PLCF#INSTALLATION_SLOT]` to the ESS-name of the device and copy the text between the triple quotes to the EPICS db.

## Supported KEYWORDs

### PV_ALIAS

Adds aliases. [More details](#specifying-aliases)

### ARCHIVE and ARCHIVE_DESC

Controls archiving requirements. [More details](#specifying-archiving-requirements)

### VALIDITY_PV and VALIDITY_CONDITION

Controls validity requirements. [More details](#specifying-validity-requirements)

### ALARM_IF

Controls the alarm severity condition of alarm PVs. [More details](#alarm-variable)

### ALARM_IS_LATCHING

Controls wether the alarm should be latched or not (applies to the `BEAST` output only). Valid for alarm PVs only.

### ALARM_IS_ANNUNCIATING

Controls wether the alarm should be annunciated or not (applies to the `BEAST` output only). Valid for alarm PVs only.

### USE_GATEWAY_DB

Controls whether the variable is defined in the GatewayDatablock or not.

This keyword can be used to specify if a variable is defined in the gateway datablock when the `PLC-EPICS-COMMS: GatewayDatablock` PLC property is set to the name of the gateway datablock. The default value is `True`, use `False` if you want to override that.

## Specifying archiving requirements

If a variable has to be archived the **`ARCHIVE=<spec>`** construction can be used. <spec> can be one of the following:

*   **`True`**; the variable will be archived with the default _policy_ of Archiver Appliance
*   **`"<policy>"`**; the variable will be archived with the specified policy of Archiver Appliance

The specifications will be collected in a file ending with _.archive_. This file has to be uploaded to the relevant archiver configuration repository.

If **`PV_DESC=<desc>`** or **`ARCHIVE_DESC=<desc>`** is specified (**`ARCHIVE_DESC`** overrides **`PV_DESC`**) it will be added as a comment before the PV name in the output.

## Specifying aliases

It is possible to specify aliases for a variable with the **`PV_ALIAS`** parameter.

*   `add_analog("primary_name",  "INT",  PV_ALIAS="secondary_name")`
*   `add_analog("primary_name",  "INT",  PV_ALIAS=["secondary_name", "tertiary_name"])`

## Specifying validity requirements

It is possible to assign a PV that controls the validity state (setting the EPICS alarm severity to INVALID) of a **status** PV coming from the PLC. This assignment is done with the **`VALIDITY_PV`** keyword. (Self assignment is ignored; if a PV is assigned to itself as a validity PV). If the specified validity PV is defined in the interface definition file then it is not necessary to specify the full PV name (i.e. the ESS name can be omitted). The validity PV can even be external; i.e. not coming from the PLC.

The condition that determines if the validity PV shows a valid state is specified by:

*   the **`VALIDITY_CONDITION`** keyword of the validity PV
*   the **`external_validity_pv("external_pv_name", <condition>)`** if the validity PV is external

The syntax of the condition:

*   it can be **`True`** if a non-zero value means validity; **`VALIDITY_CONDITION=True`**
*   it can be **`False`** if a zero value means validity; **`VALIDITY_CONDITION=False`**
*   a complex expression (evaluated by the `calc` record so valid expressions are those accepted by `calc`) where **`A`** represents the actual value of the validity PV; **`VALIDITY_CONDITION="2 < A && A < 5"`**

Restrictions:

*   Only one validity PV can be assigned to a PV (but a validity PV can be assigned to any number of PVs)
*   The validity condition is assigned to the validity PV

An actual use-case:

Safety systems use a gateway PLC between the IOC and the safety PLC and this brings in an interesting point of failure; if the connection between the two PLCs is disrupted the data sent to EPICS by the gateway PLC becomes stale/invalid. To reflect this in the state of the PVs the gateway PLC exports a status PV showing the connection status between the two PLCs. This PV is then used as the validity PV of the PVs relayed from the safety PLC.


## Specifying defaults

**`set_defaults`** can be used to define global and/or variable type specific default values. `set_defaults` calls are cumulative; new defaults will be added to the previous ones. Values specified when adding a variable take precedence.

**`clear_defaults`** can be used to clear defaults that were set so far for a variable.

### Setting defaults for everything

*   **`set_defaults(KEYWORD1="value"[, KEYWORD2="value"]...)`**
    *   This has the same effect as specifying `KEYWORD1="value"`, `KEYWORD2="value"`, and so on for every variable
    *   **`set_defaults(ARCHIVE=True)`**

### Setting defaults for certain variable types

*   **`set_defaults(<add_type1>[, <add_type2>]... ,KEYWORD1="value"[, KEYWORD2="value"]...)`**
    *   This has the same effect as specifying `KEYWORD1="value"`, `KEYWORD2="value"`, and so on for every `add_type1`, `add_type2` construct
    *   **`set_defaults(add_minor_alarm, ALARM_IF=False)`**

## Examples

### Alarm limit examples

#### Low alarm limit

*   `add_analog("Measurement_Minimum", "REAL")`
*   `add_analog("Measurement",  "REAL")`
*   `set_minor_low_limit_from("Measurement_Minimum")`
    *   Creates two variables: `Measurement_Minimum` and `Measurement` and sets the `LSV` field of `Measurement` to "MINOR" and the `LOW` field to the value of `Measurement_Minimum`
    *   Created PVs if device name is `Device_name`:
        *   `Device_name:Measurement_Minimum`
        *   `Device_name:Measurement`

#### 'Explicitly-external' alarm limit

*   `add_analog("Measurement", "REAL")`
*   `set_major_low_limit_from("Measurement_Minimum", EXTERNAL_PV=True)`
    *   Creates one variable: `Measurement` and sets the `LLSV` field of `Measurement` to "MAJOR" and the `LOLO` field to the value of `Measurement_Minimum`
    *   Created PVs if device name is `Device_name`:
        *   `Device_name:Measurement`
    *   `Measurement_Minimum` shall be defined outside of PLCFactory

#### 'Implicitly-external' alarm limit

*   `add_analog("Measurement", "REAL")`
*   `set_major_low_limit_from("External_Device:Measurement_Minimum")`
    *   Creates one variable: `Measurement` and sets the `LLSV` field of `Measurement` to "MAJOR" and the `LOLO` field to the value of `External_Device:Measurement_Minimum`
    *   Created PVs if device name is `Device_name`:
        *   `Device_name:Measurement`
    *   `External_Device:Measurement_Minimum` shall be defined outside of PLCFactory or in an Interface Definition file of `External_Device`

#### Low and high alarm limits

*   `add_analog("Measurement",  "REAL")`
*   `add_minor_low_limit("Measurement_Minimum")`
*   `add_major_high_limit("Measurement_Maximum")`
    *   Creates three variables: `Measurement`, `Measurement_Minimum`, and `Measurement_Maximum` and sets the `LSV` field of `Measurement` to "MINOR", the `HHSV` field to "MAJOR", the `LOW` field to the value of `Measurement_Minimum`, and the `HIHI` field to the value of `Measurement_Maximum`

### Drive limit examples

*   `add_analog("Setpoint", "REAL")`
*   `set_low_drive_limit_from("LowestAllowedSetpoint")`
*   `set_high_drive_limit_from("HighestAllowedSetpoint")`
    *   Creates one variable: `Setpoint` and sets the `DRVL` field of `Setpoint` to the value of `LowestAllowedSetpoint` and the `DRVH` field of `Setpoint` to the value of `HighestAllowedSetpoint`

### Archiving examples

#### Default archiving policy

*   `add_digital("Error",`             **`ARCHIVE=True`**`)`
    *   Archive with the default policy

#### Custom archiving policy

*   `add_analog("ErrorCodeR", "INT",`  **`ARCHIVE="1Hz"`**`)`
    *   Archive with the 1Hz policy

### Validity examples

#### Simple validity condition

*   `add_digital("RIO_Connected", VALIDITY_CONDITION=True)`
*   `add_analog("AI0", VALIDITY_PV="RIO_Connected")`
    *   `AI0` will be set to INVALID alarm severity if `RIO_Connected` is false

#### Complex validity condition

*   `add_analog("Voltage_Level", VALIDITY_CONDITION="4.5 <= A && A <= 5.5")`
*   `add_analog("Reading", VALIDITY_PV="Voltage_Level")`
    *   `Reading` will be set to INVALID alarm severity if `Voltage_Level` is less than 4.5 or greater than 5.5

#### External validity PV

*   `add_analog("foo", VALIDITY_PV="sys-subsys:dis-dev-idx:bar")`
*   `external_validity_pv("sys-subsys:dis-dev-idx:bar", VALIDITY_CONDITION=False)`
    *   `foo` will be set to INVALID alarm severity if `sys-subsys:dis-dev-idx:bar` is true or not connected

#### External validity PV

*   `add_analog("foo", VALIDITY_PV="sys-subsys:dis-dev-idx:bar")`
*   `external_validity_pv("sys-subsys:dis-dev-idx:bar", False)`
    *   The same as the previous but `VALIDITY_CONDITION` is not spelled out

### Gateway datablock examples

Suppose the `PLC-EPICS-COMMS: GatewayDatablock` is set to `dbSTD_to_Gateway`.
*   `add_analog("foo")`
    *    The variable `foo` will be interpreted as `"dbSTD_to_Gateway"."foo"` and will not be declared in the generated instance DB
*   `add_analog("bar", USE_GATEWAY_DB=False)`
    *    The variable `bar` will be declared in the generated instance DB. From this variable's point of view it is as if `PLC-EPICS-COMMS: GatewayDatablock` was not set
