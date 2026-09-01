import shutil

from collections.abc import Iterator

from contextlib import contextmanager

from pathlib import Path

from uuid import uuid4



from core.config import get_app_temp_dir



@contextmanager
def app_temp_dir(prefix: str) -> Iterator[Path]:

    base_dir = get_app_temp_dir()

    for _ in range(20):

        path = base_dir / f"{prefix}{uuid4().hex}"

        try:

            path.mkdir()

        except FileExistsError:

            continue

        break

    else:

        raise RuntimeError("не удалось создать временную папку")

    try:

        yield path

    finally:

        shutil.rmtree(path, ignore_errors=True)
