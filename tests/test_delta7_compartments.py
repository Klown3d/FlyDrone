import pytest
from flydrone.morphology.delta7_compartments import pb_name, pattern_name


def test_bridge_index_convention_and_pattern_order():
    assert [pb_name(i) for i in (1,9,10,18)]==['L9','L1','R1','R9']
    assert pattern_name(['PB14','PB06'])=='L4R5'
    assert pattern_name(['PB13','PB04'])=='L6R4'
    with pytest.raises(ValueError):
        pb_name(19)
