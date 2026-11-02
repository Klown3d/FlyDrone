import pyarrow as pa
from flydrone.data.extract_recurrent_synapses import internal_mask


def test_internal_mask_requires_both_endpoints():
    batch=pa.record_batch({'pre_pt_root_id':[1,1,9],'post_pt_root_id':[2,9,2]})
    mask=internal_mask(batch,pa.array([1,2]))
    assert mask.to_pylist()==[True,False,False]
