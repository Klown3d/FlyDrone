from pathlib import Path
import numpy as np
import yaml
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.connectome_nulls import degree_preserving_rewire,block_degree_preserving_rewire
from flydrone.simulation.benchmark_circuit_ablation import uniform_support,variants


def test_uniform_support_preserves_edges_and_normalizes_rows():
    weights=np.array([[0.,.2,.8],[.5,0.,.5]])
    uniform=uniform_support(weights)
    np.testing.assert_array_equal(uniform>0,weights>0);np.testing.assert_allclose(uniform.sum(axis=1),1)
    np.testing.assert_allclose(uniform[0],[0,.5,.5])


def test_randomized_variants_preserve_every_row_multiset():
    root=Path(__file__).resolve().parents[1];b=yaml.safe_load((root/'configs/orientation_candidate_v1.yaml').read_text());model=EPGDelta7Candidate(root,root/b['candidate_config'])
    shuffled=variants(model,[901])[-1][1]
    for name,original in [('epg_to_delta',model.epg_to_delta),('delta_to_pfl3',model.delta_to_pfl3),('fc2_weights',model.base.fc2_weights)]:
        np.testing.assert_allclose(np.sort(shuffled[name],axis=1),np.sort(original,axis=1))


def test_degree_preserving_rewire_keeps_degrees_and_row_weights():
    weights=np.array([[.2,.8,0,0],[0,.3,.7,0],[.4,0,0,.6],[0,0,.5,.5]])
    changed,accepted=degree_preserving_rewire(weights,np.random.default_rng(11),20)
    assert accepted>0 and not np.array_equal(changed,weights)
    np.testing.assert_array_equal((changed>0).sum(axis=1),(weights>0).sum(axis=1))
    np.testing.assert_array_equal((changed>0).sum(axis=0),(weights>0).sum(axis=0))
    np.testing.assert_allclose(np.sort(changed,axis=1),np.sort(weights,axis=1))


def test_block_rewire_preserves_degrees_and_weights_inside_each_group():
    weights=np.array([[.2,.8,0,0,.3,.7,0,0],[0,.3,.7,0,0,.4,.6,0],[.4,0,0,.6,.2,0,0,.8],[0,0,.5,.5,0,0,.1,.9]])
    groups=np.array(['a']*4+['b']*4)
    changed,accepted=block_degree_preserving_rewire(weights,groups,np.random.default_rng(17),20)
    assert accepted>0 and not np.array_equal(changed,weights)
    for group in ('a','b'):
        selected=groups==group
        np.testing.assert_array_equal((changed[:,selected]>0).sum(axis=0),(weights[:,selected]>0).sum(axis=0))
        np.testing.assert_array_equal((changed[:,selected]>0).sum(axis=1),(weights[:,selected]>0).sum(axis=1))
        np.testing.assert_allclose(np.sort(changed[:,selected],axis=1),np.sort(weights[:,selected],axis=1))
