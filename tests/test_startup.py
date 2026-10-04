import pytest
from sqlalchemy.exc import OperationalError

import main


def _err():
    return OperationalError("stmt", {}, Exception("Connection refused"))


def test_init_db_retries_until_db_ready(monkeypatch):
    calls = {"n": 0}

    def flaky(bind):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _err()

    monkeypatch.setattr(main.models.Base.metadata, "create_all", flaky)
    monkeypatch.setattr(main.time, "sleep", lambda s: None)
    main._init_db(retries=5, delay=0)
    assert calls["n"] == 3


def test_init_db_gives_up_after_retries(monkeypatch):
    def always_fail(bind):
        raise _err()

    monkeypatch.setattr(main.models.Base.metadata, "create_all", always_fail)
    monkeypatch.setattr(main.time, "sleep", lambda s: None)
    with pytest.raises(OperationalError):
        main._init_db(retries=3, delay=0)
