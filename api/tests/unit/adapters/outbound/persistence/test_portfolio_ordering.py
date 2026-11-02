import pytest

from adapters.outbound.persistence.portfolio_repository import natural_name_key


def _sorted(names):
    return sorted(names, key=natural_name_key)


@pytest.mark.happy_path
def test_zero_padded_prefixes_stay_in_sequence():
    assert _sorted(["03 - c", "01 - a", "02 - b"]) == ["01 - a", "02 - b", "03 - c"]


@pytest.mark.happy_path
def test_unpadded_numbers_compare_by_value():
    names = ["10 - Crypto", "2 - Savings", "1 - Cash"]
    assert _sorted(names) == ["1 - Cash", "2 - Savings", "10 - Crypto"]


@pytest.mark.happy_path
def test_case_is_ignored():
    assert _sorted(["zebra", "Banana", "apple", "Cherry"]) == [
        "apple",
        "Banana",
        "Cherry",
        "zebra",
    ]


@pytest.mark.edge_case
def test_numbers_inside_names_and_mixed_names():
    names = ["Growth", "growth 10", "Growth 2", "10 - x", "2 - y"]
    assert _sorted(names) == ["2 - y", "10 - x", "Growth", "Growth 2", "growth 10"]


@pytest.mark.edge_case
def test_sorting_is_stable_for_equal_names():
    # Equal keys keep their input order (the query returns oldest first).
    first, second = "Core", "core"
    assert natural_name_key(first) == natural_name_key(second)
    assert sorted([first, second], key=natural_name_key) == [first, second]
    assert sorted([second, first], key=natural_name_key) == [second, first]


@pytest.mark.edge_case
@pytest.mark.parametrize("name", ["", "   ", "0", "007", "名前 3"])
def test_key_handles_odd_names(name):
    assert isinstance(natural_name_key(name), tuple)
