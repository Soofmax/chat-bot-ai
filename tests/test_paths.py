from pathlib import Path
import pytest

from server.app import ensure_safe_client_id, safe_client_path


def test_ensure_safe_client_id_valid():
    assert ensure_safe_client_id("bms_ventouse") == "bms_ventouse"
    assert ensure_safe_client_id("client-123_ABC") == "client-123_ABC"


@pytest.mark.parametrize("cid", ["../evil", "client/evil", "client\\evil", "", "a"*65, "bad!id"])
def test_ensure_safe_client_id_invalid(cid):
    with pytest.raises(ValueError):
        ensure_safe_client_id(cid)


def test_safe_client_path_main():
    p = safe_client_path("main", "bms_ventouse")
    base = Path("./clients").resolve()
    assert base in Path(p).parents
    assert str(p).endswith("/clients/bms_ventouse/data.json")


def test_safe_client_path_alt():
    p = safe_client_path("alt", "bms_ventouse")
    base = Path("./rag_alt/clients").resolve()
    assert base in Path(p).parents
    assert str(p).endswith("/rag_alt/clients/bms_ventouse/data.json")