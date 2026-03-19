import io
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from typing import Generator


@contextmanager
def capture_stdio() -> Generator[tuple[io.StringIO, io.StringIO], None, None]:
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
        yield out, err


def capture_stderr_call(callable_obj, *args, **kwargs):
    err = io.StringIO()
    with redirect_stderr(err):
        result = callable_obj(*args, **kwargs)
    return result, err.getvalue()
