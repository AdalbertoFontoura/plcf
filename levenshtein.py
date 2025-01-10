""" PLC Factory: String similarity """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


"""
Compute the Levenshtein Distance of two strings

Orignal author:
Christopher P. Matthews
christophermatthews1985@gmail.com

Source:
https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python

The orignal code was published under the Creative Commons
Attribution-ShareAlike 3.0 license (CC BY-SA 3.0):
https://creativecommons.org/licenses/by-sa/3.0/

"""


def distance(s, t):
    assert isinstance(s, str)
    assert isinstance(t, str)

    if s == t:
        return 0

    elif len(s) == 0:
        return len(t)

    elif len(t) == 0:
        return len(s)

    v0 = [None] * (len(t) + 1)
    v1 = [None] * (len(t) + 1)

    for i in range(len(v0)):
        v0[i] = i

    for i in range(len(s)):

        v1[0] = i + 1

        for j in range(len(t)):
            cost = 0 if s[i] == t[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)

        for j in range(len(v0)):
            v0[j] = v1[j]

    return v1[len(t)]
