from collections.abc import Generator

from pipeline.store import DelayStore


def get_store() -> Generator[DelayStore, None, None]:
    store = DelayStore()
    try:
        yield store
    finally:
        store.close()
