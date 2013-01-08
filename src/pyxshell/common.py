# -*- coding: utf-8 -*-

import os
import re
import collections
import fnmatch

from pyxshell.pipeline import pipe


@pipe
def echo(item):
    """
    Yield a single item. Equivalent to ``iter([item])``, but nicer-looking.

        >>> list(echo(1))
        [1]
        >>> list(echo('hello'))
        ['hello']
    """
    yield item

@pipe
def cat(*args, **kwargs):
    r"""
    Read a file. Passes directly through to a call to `open()`.

        >>> src_file = __file__.replace('.pyc', '.py')
        >>> for line in cat(src_file):
        ...     if line.startswith('def cat'):
        ...          print repr(line)
        'def cat(*args, **kwargs):\n'
    """
    return iter(open(*args, **kwargs))


@pipe
def head( stdin, size=None ):
    """
    Yield only a given number of lines, then stop.

    If size=None, yield all the lines of the stream.

        >>> list( iter(range(10)) | head() )
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        >>> list( iter(range(10)) | head(5) )
        [0, 1, 2, 3, 4]
        >>> list( iter(range(10)) | head(0) )
        []
    """
    count = 0
    for line in stdin:
        if size != None and count >= size:
            raise StopIteration
        else:
            yield line
        count += 1


@pipe
def tail( stdin, size=None ):
    """
    Yield  the given number of lines at the end of the stream.

    If size=None, yield all the lines. If size!=None, it will wait for the data
    stream to end before yielding lines.

    >>> list( iter(range(10)) | tail() )
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> list( iter(range(10)) | tail(5) )
    [5, 6, 7, 8, 9]
    >>> list( iter(range(10)) | tail(0) )
    []
    """
    if size==None:
        for line in stdin:
            yield line
    else:
        # to compute the size from the end, it is mandatory to expand
        # the generator in a list
        data = list( stdin )
        # once expanded, we can access via ranges
        for line in data[len(data)-size:]:
            yield line


@pipe
def curl(url):
    """
    Fetch a URL, yielding output line-by-line.

        >>> UNLICENSE = 'http://unlicense.org/UNLICENSE'
        >>> for line in curl(UNLICENSE): # doctest: +SKIP
        ...     print line,
        This is free and unencumbered software released into the public domain.
        ...
    """
    import urllib2
    conn = urllib2.urlopen(url)
    try:
        line = conn.readline()
        while line:
            yield line
            line = conn.readline()
    finally:
        conn.close()


@pipe
def grep(stdin, pattern_src):
    """
    Filter strings on stdin for the given regex (uses :func:`re.search`).

        >>> list(iter(['cat', 'cabbage', 'conundrum', 'cathedral']) | grep(r'^ca'))
        ['cat', 'cabbage', 'cathedral']
    """
    pattern = re.compile(pattern_src)
    for line in stdin:
        if pattern.search(line):
            yield line


def is_in( line, patterns = [] ):
    for pattern in patterns:
        if pattern in line:
            return True
    return False

@pipe
def grep_in( stdin, patterns=[] ):
    """
    Filter strings on stdin for any string in a given list (uses :func:`in`).

        >>> list(iter(['cat', 'cabbage', 'conundrum', 'cathedral']) | grep_in(["cat","cab"]))
        ['cat', 'cabbage', 'cathedral']
    """
    for line in stdin:
        if is_in( line, patterns ):
            yield line


@pipe
def cut( stdin, fields=None, delimiter=None ):
    """
    Yields the fields-th items of the strings splited as a list according to the
    delimiter.
    If delimiter is None, any whitespace-like character is used to split.
    If fields is None, every field are returned.

        >>> list( iter( ["You don't NEED to follow ME","You don't NEED to follow ANYBODY!"] ) | cut(1,"NEED to"))
        [' follow ME', ' follow ANYBODY!']
        >>> list( iter( ["I say you are Lord","and I should know !","I've followed a few !"] ) | cut([4]) )
        [['Lord'], ['!'], ['!']]
        >>> list( iter( ["You don't NEED to follow ME","You don't NEED to follow ANYBODY!"] ) | cut([0,1],"NEED to"))
        [["You don't ", ' follow ME'], ["You don't ", ' follow ANYBODY!']]
        >>> list( iter( ["I say you are Lord","and I should know !","I've followed a few !"] ) | cut([4,1]) )
        [['Lord', 'say'], ['!', 'I'], ['!', 'followed']]
    """
    for string in stdin:
        if fields is None:
            yield string.split(delimiter)[:]
        elif isinstance(fields, collections.Iterable):
            data = string.split(delimiter)
            yield [data[i] for i in fields]
        else:
            yield string.split(delimiter)[fields]


@pipe
def join( stdin, delimiter=" " ):
    """
        Join every list items in the input with the given delimiter.
        The default delimiter is a space.

        >>> list( iter( ["- Yes, we are all different!\t- I'm not!"] ) | cut() | join() )
        ["- Yes, we are all different! - I'm not!"]
        >>> list( iter( ["- Yes, we are all different!\t- I'm not!"] ) | cut(delimiter="all") | join("NOT") )
        ["- Yes, we are NOT different!\t- I'm not!"]
    """
    for lst in stdin:
        yield delimiter.join(lst)


@pipe
def dos2unix( stdin ):
    """
    Replace DOS-like newline characters by UNIX-like ones.

        >>> list( iter(["dos\r\n","unix\n"]) | dos2unix()
        ['dos\n', 'unix\n']
    """
    for line in stdin:
        yield line.replace("\r\n","\n")


@pipe
def unix2dos( stdin ):
    """
    Replace UNIX-like newline characters by DOS-like ones.

        >>> list( iter(["dos\r\n","unix\n"]) | unix2dos()
        ['dos\r\n', 'unix\r\n']
    """
    for line in stdin:
        yield line.replace("\n","\r\n")


@pipe
def dir_file( paths ):
    """
    Yields the file name and its absolute path in a tuple,
    expand home and vars if necessary.
    """
    for path in paths:
        p = os.path.abspath( path )
        yield ( os.path.dirname(p),os.path.basename(p) )


@pipe
def expand( filepatterns ):
    """
    Yelds file names matching each 'filepatterns'.
    """
    if len(filepatterns) == 0:
        yield (i for i in [] )

    for base_dir,filepattern in dir_file(filepatterns):
        for dirname, dirs, files in os.walk( base_dir ):
            for filename in fnmatch.filter(files, filepattern):
                yield os.path.join(dirname, filename)


@pipe
def sed(stdin, pattern_src, replacement, exclusive=False):
    """
    Apply :func:`re.sub` to each line on stdin with the given pattern/repl.

        >>> list(iter(['cat', 'cabbage']) | sed(r'^ca', 'fu'))
        ['fut', 'fubbage']

    Upon encountering a non-matching line of input, :func:`sed` will pass it
    through as-is. If you want to change this behaviour to only yield lines
    which match the given pattern, pass `exclusive=True`::

        >>> list(iter(['cat', 'nomatch']) | sed(r'^ca', 'fu'))
        ['fut', 'nomatch']
        >>> list(iter(['cat', 'nomatch']) | sed(r'^ca', 'fu', exclusive=True))
        ['fut']
    """
    pattern = re.compile(pattern_src)
    for line in stdin:
        match = pattern.search(line)
        if match:
            yield (line[:match.start()] +
                   match.expand(replacement) +
                   line[match.end():])
        elif not exclusive:
            yield line


@pipe
def pretty_printer(stdin, **kwargs):
    """
    Pretty print each item on stdin and pass it straight through.

        >>> for item in iter([{'a': 1}, ['b', 'c', 3]]) | pretty_printer():
        ...     pass
        {'a': 1}
        ['b', 'c', 3]
    """
    import pprint
    for item in stdin:
        pprint.pprint(item, **kwargs)
        yield item


@pipe
def map(stdin, func):
    """
    Map each item on stdin through the given function.

        >>> list(xrange(5) | map(lambda x: x + 2))
        [2, 3, 4, 5, 6]
    """
    for item in stdin:
        yield func(item)


@pipe
def filter(stdin, predicate):
    """
    Only pass through items for which `predicate(item)` is truthy.

        >>> list(xrange(5) | filter(lambda x: x % 2 == 0))
        [0, 2, 4]
    """
    for item in stdin:
        if predicate(item):
            yield item


@pipe
def sh(stdin, command=None, check_success=False):
    r"""
    Run a shell command, send it input, and produce its output.

        >>> print ''.join(echo("h\ne\nl\nl\no") | sh('sort -u'))
        e
        h
        l
        o
        <BLANKLINE>
        >>> for line in sh('echo Hello World'):
        ...     print line,
        Hello World
        >>> for line in sh('false', check_success=True):
        ...     print line, # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        CalledProcessError: Command '['false']' returned non-zero exit status 1
    """
    import subprocess
    import shlex

    if command is None:
        stdin, command = (), stdin

    if isinstance(command, basestring):
        command = shlex.split(command)

    pipe = subprocess.Popen(command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)

    try:
        for line in stdin:
            pipe.stdin.write(line)
        pipe.stdin.close()
        for line in pipe.stdout:
            yield line
    finally:
        result = pipe.wait()
        if check_success and result != 0:
            raise subprocess.CalledProcessError(result, command)