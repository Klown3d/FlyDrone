from pathlib import Path
import numpy as np
import yaml
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.steering_interface import activity,command


def test_shared_interface_matches_previous_candidate_with_corrected_angles():
    root=Path(__file__).resolve().parents[1]
    b=yaml.safe_load((root/'configs/orientation_candidate_v1.yaml').read_text())
    m=EPGDelta7Candidate(root,root/b['candidate_config'])
    headings=np.deg2rad([-179,-60,0,45,179]);goals=np.deg2rad([15,-90,30,145,-60])
    rates=activity(m,headings,goals,b)[3]
    m.epg_angles_rad=-m.epg_angles_rad
    for i,(heading,goal) in enumerate(zip(headings,goals)):
        np.testing.assert_allclose(rates[i],m.rates(heading,goal,'via_delta7'),atol=1e-12)


def test_explicit_ablations_remove_only_the_named_stream():
    root=Path(__file__).resolve().parents[1];b=yaml.safe_load((root/'configs/orientation_candidate_v1.yaml').read_text());m=EPGDelta7Candidate(root,root/b['candidate_config'])
    heading=np.array([.3]);goal=np.array([-1.1])
    intact=activity(m,heading,goal,b);no_delta=activity(m,heading,goal,b,{'delta7_enabled':False});no_fc2=activity(m,heading,goal,b,{'fc2_enabled':False})
    assert np.any(intact[1]) and np.any(intact[2])
    assert not np.any(no_delta[1]) and np.any(no_delta[2])
    assert np.any(no_fc2[1]) and not np.any(no_fc2[2])
    assert command(m,heading,goal,b,False,{'delta7_enabled':False})[0].shape==(1,)
