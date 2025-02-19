from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: PLCF# Language """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


"""
This module processes expressions in 'PLCFLang', the embedded domain-specific
language of PLC Factory. Please see the documentation for further details.

Note that erroneous input in syntactically valid expressions, for instance
using a variable name that is not defined as a device property in CCDB,
will not lead to an error. Instead, such input is simply returned unchanged.
"""


# Python libraries

# PLC Factory modules
import plcf_glob       as glob
import plcf_ext



class PLCFException(Exception):
    pass



class PLCFSyntaxError(PLCFException):
    pass



class PLCFNoWordException(PLCFException):
    pass



class PLCFNoPropertyException(PLCFException):
    pass



class PLCFNoBacktrackPropertyException(PLCFNoPropertyException):
    pass



class PLCFEvalException(PLCFException):
    def __init__(self, expression, exception, *args):
        super(PLCFEvalException, self).__init__(*args)
        self.expression = expression
        self.exception  = exception


    def __str__(self):
        return "The following exception occured during the evaluation of '{expr}': {exc}: {msg}".format(expr = self.expression,
                                                                                                        exc  = type(self.exception).__name__,
                                                                                                        msg  = str(self.exception))



class PLCF(object):
    plcf_tag         = "[PLCF#"
    plcf_tag_len     = len(plcf_tag)
    plcf_up          = "^("
    plcf_up_len      = len(plcf_up)
    plcf_counter_tag = "#COUNTER"
    plcf_counter     = "Counter"
    num_of_counters  = 9

    @staticmethod
    def __specialProperties(device):
        sp = { 'TIMESTAMP'                 :  glob.timestamp,
               'ROOT_INSTALLATION_SLOT'    :  plcf_ext.extra_colon(glob.root_installation_slot),
               'RAW_ROOT_INSTALLATION_SLOT' : glob.root_installation_slot
             }

        if device is not None:
            sp.update({ 'INSTALLATION_SLOT'       : plcf_ext.extra_colon(device.name()),
                        'RAW_INSTALLATION_SLOT'   : device.name(),
                        'INSTALLATION_SLOT_DESC'  : device.description(),
                        'DEVICE_TYPE'             : device.deviceType(),
                      })

        return sp


    @staticmethod
    def get_counter(idx):
        if idx > PLCF.num_of_counters or idx < 1:
            raise IndexError("Counter index must be between 1..{}".format(PLCF.num_of_counters))

        return "{}{}".format(PLCF.plcf_counter, idx)


    @staticmethod
    def initializeCounters():
        counters = dict()

        for n in range(PLCF.num_of_counters):
            counters[PLCF.plcf_counter + str(n + 1)] = 0

        return counters


    def __init__(self, device):
        self._device  = device
        self._evalenv = { "ext": plcf_ext }

        """
        Sorting property names from longest to shortest avoids
        the potential issue that a PLCF# expression can't be fully
        evaluated when a property name is part of another property name of
        the same device.

        In more technical terms: the list of propery names that are
        retrieved via the method keys() is neither sorted nor deterministic,
        i.e. multiple calls may result in different permutations of the
        same elements.

        In PLC Factory, property names are processed one by one, as they
        are encountered (see the for-loop below). Further, there is no
        semantic analysis of PLCF# expressions. Thus, without
        sorting, it may happen that a property name "foo" is processed before
        a property name "foobar", but processing the former would leave "bar"
        in the resulting expression. This would be bad enough, but imagine
        what would happen if there was a property name "bar" left to process!

        With sorting by property names by length in reverse, i.e. from longest
        to shortest, "foobar" is processed before "foo", so the issue described
        above is entirely avoided. For the curious, this approach is similar
        to the "maximal munch" concept in compiler theory.
        """

        if device is not None:
            # Need to use dict() to create a new instance
            #  as it will be modified locally
            self._properties = dict(device.propertiesDict())
        else:
            self._properties = dict()
        self._keys = list(self._properties.keys())

        sp   = self.__specialProperties(device)
        # Pre-register a TEMPLATE property without an actual value
        keys = list(sp.keys())
        keys.append('TEMPLATE')

        if not set(keys).isdisjoint((self._keys)):
            raise PLCFException("Redefinition of the following reserved properties is not allowed: {}".format(set(self._keys).intersection(set(keys))))

        self._keys.extend(keys)
        self._keys.sort(key = lambda s: len(s), reverse = True)

        self._properties.update(sp)


    def register_template(self, templateId):
        self._properties['TEMPLATE'] = 'template-' + templateId


    def process(self, line_or_lines):
        if isinstance(line_or_lines, str):
            return self.processLine(line_or_lines)

        # read each line, process them, add one by one to accumulator
        return [self.processLine(x) for x in line_or_lines]


    # extracts a PLCFLang expression from a line in a template,
    # evaluates the expression, and returns a new line with
    # the result of the evaluation
    def processLine(self, line):
        assert isinstance(line, str)

        result = ""
        while True:
            # recurse until all PLCF_Lang expressions have been processed
            (start, expression, end) = self.getPLCFExpression(line)

            if expression is None:
                return result + line

            reduced = self._evaluateExpression(expression)

            # maintain PLCF tag if a counter variable is part of the expression
            if PLCF.hasCounter(reduced):
                result += line[:start] + self.plcf_tag + reduced + "]"
            else:
                result += line[:start] + reduced

            line = line[end + 1:]


    def _evalUp(self, expression):
        assert isinstance(expression, str)

        while True:
            # extract property
            start = expression.find(self.plcf_up)
            if start == -1:
                break

            # FIXME: which one makes more sense?
            end   = expression.find(")", start)
#            end   = PLCF.findMatchingParenthesis(expression[start:], '()') + start
            prop  = expression[start + self.plcf_up_len:end]

            # backtrack
            val  = self._device.backtrack(prop)
            expression = expression[:start] + val + expression[end + 1:]

        return expression


    def _check_infinite_recursion(self, expression, barrier):
        expression = self._evalUp(expression)
        for elem in self._keys:
            # Found infinite recursion
            if elem == barrier:
                return True

            # Caught a longer match, no infinite recursion
            if elem in expression:
                break

        return False


    # replaces all variables in a PLCFLang expression with values
    # from CCDB and returns the evaluated expression
    def _evaluateExpression(self, expression):
        assert isinstance(expression, str)

        # resolve all references to properties in devices on a higher level
        # in the hierarchy
        expression = self._evalUp(expression)

        for elem in self._keys:
            try:
                if elem in expression:
                    value                = self._properties.get(elem)
                    if value is None:
                        raise PLCFException("Property '{}' has no value. Fix CCDB configuration: {}".format(elem, self._device.url()))
                    (tmp, pos_after_val) = self.substituteWord(expression, elem, value)
                    # If the substitution string ('value') contains the key ('elem') then check if the result contains other keys than 'elem'
                    # In other words: try to avoid an infinite recursion
                    # Not sure if this can still happen now that we don't substitute inside words but let's keep it here for now
                    if elem in value and self._check_infinite_recursion(tmp, elem):
                        tmp = tmp[:pos_after_val] + self._evaluateExpression(tmp[pos_after_val:])
                        expression = self._evalUp(tmp)
                        break
                    # recursion to take care of multiple occurrences of variables
                    return self._evaluateExpression(tmp)
            except PLCFNoWordException:
                pass

        # evaluation happens after all substitutions have been performed
        wasquoted = False
        #Do not evaluate expressions which consist solely of a quoted string
        if (expression.startswith('"') and expression.endswith('"') and expression.count('"') == 2) or \
           (expression.startswith("'") and expression.endswith("'") and expression.count("'") == 2):
            wasquoted = expression[0]

        if "ext." in expression: #expression.startswith("ext."):
            try:
                #Evaluate ext module call
                result = eval(expression, self._evalenv)
            except plcf_ext.PLCFExtException as e:
                raise e #from None
            except Exception as e:
                raise PLCFEvalException(expression, e) #from None
        else:
            try:
                #Evaluate this expression
                result = eval(expression)
                if wasquoted:
                    result = wasquoted + result + wasquoted
            # catch references to slot names (and erroneous input)
            except (SyntaxError, NameError) as e:
                result = expression
            except Exception as e:
                raise PLCFEvalException(expression, e) #from None

        return str(result)


    def getProperty(self, prop):
        """
        Returns the value of property 'prop' or raises PLCFNoPropertyException if not found
        """
        
        if prop.startswith(self.plcf_up):
            if prop.find(')') != len(prop) - 1:
                raise PLCFSyntaxError("Invalid backtrack expression")
            prop = prop[self.plcf_up_len : -1]
            try:
                return self._device.backtrack(prop, PLCFNoBacktrackPropertyException)
            except PLCFNoBacktrackPropertyException as e:
                raise e
            except Exception as e:
                raise PLCFException(e)

        try:
            return self._properties[prop]
        except KeyError:
            raise PLCFNoPropertyException(prop)


    @staticmethod
    def isWordChar(char):
        return char.isalnum() or char == '_'


    @staticmethod
    def hasCounter(line, counter = None):
        start = -1;
        while True:
            try:
                start = line.index(counter if counter else PLCF.plcf_counter, start + 1)
            except ValueError:
                return False

            # Check if the preceding character is alphanumeric, if it is, then the "Counter" is part of a word
            if start and PLCF.isWordChar(line[start - 1]):
                continue

            try:
                if counter is None:
                    # Counter is not explicitly specified but check if the following character is a number, if not then the counter is not ours
                    if not line[start + len(PLCF.plcf_counter)].isdigit():
                        continue

                    # Let's define a counter and check with that too
                    counter = PLCF.plcf_counter + "1"
            except IndexError as e:
                # End-of-string, there was nothing after PLCF.plcf_counter
                return False

            try:
                # Check if the following character is alphanumeric, if it is, then the counter is part of a word
                if PLCF.isWordChar(line[start + len(counter)]):
                    continue
            except IndexError as e:
                # End-of-string, it was a counter
                return True

            return True


    @staticmethod
    def wordIndex(line, word):
        start = -1
        while True:
            try:
                start = line.index(word, start + 1)
            except ValueError as e:
                raise PLCFNoWordException(e)

            # Check if the preceding character is alphanumeric, if it is, then "word" is part of a word
            if start and PLCF.isWordChar(line[start - 1]):
                continue

            try:
                # Check if the next character is alphanumeric; if it isn't then "word" is a standalone word
                if not PLCF.isWordChar(line[start + len(word)]):
                    return start
            except IndexError:
                return start


    @staticmethod
    def evalCounters(lines, counters = None):
        assert isinstance(lines, list)

        if counters is None:
            counters = PLCF.initializeCounters()
        elif not isinstance(counters, dict):
            raise PLCFException("Invalid counters type")
        elif len(counters) > PLCF.num_of_counters:
            raise PLCFException("Too many counters")

        output = []

        for line in lines:
            if PLCF.plcf_tag in line:
                if PLCF.plcf_counter_tag not in line:
                    line = PLCF._evalCounter(line, counters)
                else:
                    (counters, line) = PLCF._evalCounterIncrease(line, counters)

            assert isinstance(line, str)
            # PLCF should now all be processed
            if PLCF.plcf_tag in line:
                raise PLCFException("Leftover PLCF# expression in line: {line}".format(line = line))

            output.append(line)

        return (output, counters)


    @staticmethod
    def _evalCounter(line, counters):
        assert isinstance(line,     str )
        assert isinstance(counters, dict)

        s = 0
        while True:
            # Check if PLCF# expressions are valid
            (_, expr, e) = PLCF.getPLCFExpression(line[s:])
            if e is None:
                break
            s += e + 1

        # substitutions
        for key in counters.keys():
            try:
                while True:
                    (line, _) = PLCF.substituteWord(line, key, str(counters[key]), True)
            except PLCFNoWordException:
                pass

        # evaluation
        while True:
            (expr, line) = PLCF._processLineCounter(line)
            if expr is None:
                return line


    @staticmethod
    def _evalCounterIncrease(line, counters):
        assert isinstance(line, str)
        assert isinstance(counters, dict)

        # identify start of expression and substitute
        (pos, _, _) = PLCF.getPLCFExpression(line)

        if pos is not None:
            pre  = line[:pos]
            post = line[pos:]

            for key in counters.keys():
                try:
                    (post, _) = PLCF.substituteWord(post, key, str(counters[key]))
                except PLCFNoWordException:
                    pass

            line = pre + post

        # identify counter
        counterVar = line.split()[1]
        if counterVar not in counters.keys():
            raise PLCFSyntaxError("Unknown counter: {} in line {}".format(counterVar, line))

        # evaluate
        (counter, line) = PLCF._processLineCounter(line)
        assert isinstance(counter, int), counter
        assert isinstance(line,    str)

        for key in counters.keys():
            if counterVar == key:
                counters[key] = counter

        return (counters, line)


    @staticmethod
    def _processLineCounter(line):
        assert isinstance(line, str)

        (start, expression, end) = PLCF.getPLCFExpression(line)

        if expression is None:
            return (None, line)

        result = ""

        # evaluation happens after all substitutions have been performed
        try:
            result = eval(expression)

        # catch references to slot names (and erroneous input)
        except (SyntaxError, NameError) as e:
            result = expression

        return (result, line[:start] + str(result) + line[end + 1:])


    @staticmethod
    def getPLCFExpression(line):
        assert isinstance(line, str)

        start = line.find(PLCF.plcf_tag)

        if start == -1:
            return (None, None, None) # nothing to replace

        try:
            end = PLCF.findMatchingParenthesis(line[start:], '[]') + start
        except PLCFException as e:
            raise PLCFSyntaxError("Malformatted PLCF# expression ({error}) in line {line}".format(error = e.args[0], line = line))

        if end == -1:
            raise PLCFSyntaxError("Unclosed PLCF# expression in line {line}".format(line = line))

        expression = line[start + PLCF.plcf_tag_len : end]
        if not PLCF.matchingParentheses(expression):
            raise PLCFSyntaxError("Invalid parentheses expression in line {}".format(line))

        return (start, expression, end)


    #Returns the index of the closing paren which matches the first opening paren
    @staticmethod
    def findMatchingParenthesis(line, paren):
        istart = []  # stack of indices of opening parentheses
        d      = []
        oparen = paren[0]
        cparen = paren[1]

        for i, c in enumerate(line):
            if c == oparen:
                istart.append(i)
            elif c == cparen:
                try:
                    ci = istart.pop()
                    if not istart:   # check if this closed the first opening parenthesis
                        return i

                    d.append([ci, i])
                except IndexError:
                    raise PLCFSyntaxError('Too many closing parentheses')

        if istart:  # check if stack is empty afterwards
            raise PLCFSyntaxError('Too many opening parentheses')

        d.sort()

        return d[0][1]


    # substitutes a variable in an expression with the provided value
    @staticmethod
    def substituteWord(expr, word, value, exception_if_not_found = False):
        assert isinstance(expr,   str), (expr, type(expr))
        assert isinstance(word,   str), (expr, word, type(word))
        assert isinstance(value,  str), (expr, word, value, type(value))

        if word not in expr:
            if exception_if_not_found:
                raise PLCFNoWordException()
            return (expr, len(expr))

        start           = PLCF.wordIndex(expr, word)
        end             = start + len(word)
        pos_after_value = start + len(value)

        return (expr[:start] + value + expr[end:], pos_after_value)


    # checks for basic validity of expression by determining whether
    # open and closed parentheses match
    @staticmethod
    def matchingParentheses(line):
        assert isinstance(line, str)

        acc = 0
        for c in line:
            if c == '(':
                acc += 1
            elif c == ')':
                acc -= 1

            if acc < 0:
                return False

        return acc == 0




if __name__ == "__main__":
    import test_plcf
    test_plcf.unittest.main(test_plcf)
