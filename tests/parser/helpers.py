from __future__ import annotations

import collections
import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import unittest


FS_NONASCII = ""
TESTFN_ASCII = "@test"

TESTFN_ASCII = f"{TESTFN_ASCII}_{os.getpid()}_tmp"
if FS_NONASCII:
    TESTFN_NONASCII = TESTFN_ASCII + FS_NONASCII
else:
    TESTFN_NONASCII = None
TESTFN = TESTFN_NONASCII or TESTFN_ASCII
TESTFN_UNENCODABLE = None
is_apple = sys.platform in {"ios", "tvos", "watchos", "darwin"}

if os.name == "nt":
    # skip win32s (0) or Windows 9x/ME (1)
    if sys.getwindowsversion().platform >= 2:
        # Different kinds of characters from various languages to minimize the
        # probability that the whole name is encodable to MBCS (issue #9819)
        TESTFN_UNENCODABLE = TESTFN_ASCII + "-\u5171\u0141\u2661\u0363\udc80"
        try:
            TESTFN_UNENCODABLE.encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            pass
        else:
            print(
                "WARNING: The filename %r CAN be encoded by the filesystem "
                "encoding (%s). Unicode filename tests may not be effective"
                % (TESTFN_UNENCODABLE, sys.getfilesystemencoding())
            )
            TESTFN_UNENCODABLE = None
# Apple and Emscripten deny unencodable filenames (invalid utf-8)
elif not is_apple and sys.platform not in {"emscripten", "wasi"}:
    try:
        # ascii and utf-8 cannot encode the byte 0xff
        b"\xff".decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        # 0xff will be encoded using the surrogate character u+DCFF
        TESTFN_UNENCODABLE = TESTFN_ASCII + b"-\xff".decode(
            sys.getfilesystemencoding(), "surrogateescape"
        )
    else:
        # File system encoding (eg. ISO-8859-* encodings) can encode
        # the byte 0xff. Skip some unicode filename tests.
        pass

TESTFN_UNDECODABLE = None
for name in (
    # b'\xff' is not decodable by os.fsdecode() with code page 932. Windows
    # accepts it to create a file or a directory, or don't accept to enter to
    # such directory (when the bytes name is used). So test b'\xe7' first:
    # it is not decodable from cp932.
    b"\xe7w\xf0",
    # undecodable from ASCII, UTF-8
    b"\xff",
    # undecodable from iso8859-3, iso8859-6, iso8859-7, cp424, iso8859-8, cp856
    # and cp857
    b"\xae\xd5"
    # undecodable from UTF-8 (UNIX and Mac OS X)
    b"\xed\xb2\x80",
    b"\xed\xb4\x80",
    # undecodable from shift_jis, cp869, cp874, cp932, cp1250, cp1251, cp1252,
    # cp1253, cp1254, cp1255, cp1257, cp1258
    b"\x81\x98",
):
    try:
        name.decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        try:
            name.decode(sys.getfilesystemencoding(), sys.getfilesystemencodeerrors())
        except UnicodeDecodeError:
            continue
        TESTFN_UNDECODABLE = os.fsencode(TESTFN_ASCII) + name
        break
_can_chmod = None


def can_chmod():
    global _can_chmod
    if _can_chmod is not None:
        return _can_chmod
    if not hasattr(os, "chmod"):
        _can_chmod = False
        return _can_chmod
    try:
        with open(TESTFN, "wb") as f:
            try:
                os.chmod(TESTFN, 0o555)
                mode1 = os.stat(TESTFN).st_mode
                os.chmod(TESTFN, 0o777)
                mode2 = os.stat(TESTFN).st_mode
            except OSError:
                can = False
            else:
                can = stat.S_IMODE(mode1) != stat.S_IMODE(mode2)
    finally:
        os.unlink(TESTFN)
    _can_chmod = can
    return can


def skip_unless_working_chmod(test):
    """Skip tests that require working os.chmod()

    WASI SDK 15.0 cannot change file mode bits.
    """
    ok = can_chmod()
    msg = "requires working os.chmod()"
    return test if ok else unittest.skip(msg)(test)


# Check whether the current effective user has the capability to override
# DAC (discretionary access control). Typically user root is able to
# bypass file read, write, and execute permission checks. The capability
# is independent of the effective user. See capabilities(7).
_can_dac_override = None


def can_dac_override():
    global _can_dac_override

    if not can_chmod():
        _can_dac_override = False
    if _can_dac_override is not None:
        return _can_dac_override

    try:
        with open(TESTFN, "wb") as f:
            os.chmod(TESTFN, 0o400)
            try:
                with open(TESTFN, "wb"):
                    pass
            except OSError:
                _can_dac_override = False
            else:
                _can_dac_override = True
    finally:
        try:
            os.chmod(TESTFN, 0o700)
        except OSError:
            pass
        os.unlink(TESTFN)

    return _can_dac_override


def skip_if_dac_override(test):
    ok = not can_dac_override()
    msg = "incompatible with CAP_DAC_OVERRIDE"
    return test if ok else unittest.skip(msg)(test)


@contextlib.contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO."""
    import io

    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, io.StringIO())
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


def captured_stdout():
    """Capture the output of sys.stdout:

    with captured_stdout() as stdout:
        print("hello")
    self.assertEqual(stdout.getvalue(), "hello\\n")
    """
    return captured_output("stdout")


def captured_stderr():
    """Capture the output of sys.stderr:

    with captured_stderr() as stderr:
        print("hello", file=sys.stderr)
    self.assertEqual(stderr.getvalue(), "hello\\n")
    """
    return captured_output("stderr")


class EnvironmentVarGuard(collections.abc.MutableMapping):
    """Class to help protect the environment variable properly.  Can be used as
    a context manager."""

    def __init__(self):
        self._environ = os.environ
        self._changed = {}

    def __getitem__(self, envvar):
        return self._environ[envvar]

    def __setitem__(self, envvar, value):
        # Remember the initial value on the first access
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        self._environ[envvar] = value

    def __delitem__(self, envvar):
        # Remember the initial value on the first access
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        if envvar in self._environ:
            del self._environ[envvar]

    def keys(self):
        return self._environ.keys()

    def __iter__(self):
        return iter(self._environ)

    def __len__(self):
        return len(self._environ)

    def set(self, envvar, value):
        self[envvar] = value

    def unset(self, envvar):
        del self[envvar]

    def copy(self):
        # We do what os.environ.copy() does.
        return dict(self)

    def __enter__(self):
        return self

    def __exit__(self, *ignore_exc):
        for k, v in self._changed.items():
            if v is None:
                if k in self._environ:
                    del self._environ[k]
            else:
                self._environ[k] = v
        os.environ = self._environ


class StdIOBuffer(io.TextIOWrapper):
    """Replacement for writable io.StringIO that behaves more like real file

    Unlike StringIO, provides a buffer attribute that holds the underlying
    binary data, allowing it to replace sys.stdout/sys.stderr in more
    contexts.
    """

    def __init__(self, initial_value="", newline="\n"):
        initial_value = initial_value.encode("utf-8")
        super().__init__(
            io.BufferedWriter(io.BytesIO(initial_value)), "utf-8", newline=newline
        )

    def getvalue(self):
        self.flush()
        return self.buffer.raw.getvalue().decode("utf-8")


@skip_unless_working_chmod
class TempDirMixin:
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_dir = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.old_dir)
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.chmod(os.path.join(self.temp_dir, name), stat.S_IWRITE)
        shutil.rmtree(self.temp_dir, True)

    def create_writable_file(self, filename):
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(filename)
        return file_path

    def create_readonly_file(self, filename):
        os.chmod(self.create_writable_file(filename), stat.S_IREAD)


class Sig:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
