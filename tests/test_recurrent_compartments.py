import numpy as np
import pandas as pd
from flydrone.neural.recurrent_compartments import projection_compartments


def test_projection_fractions_sum_to_one():
    edges=pd.DataFrame({'pre_type':['A','A','A'],'post_type':['B','B','C'],'neuropil':['PB','EB','PB'],'syn_count':[3,1,2]})
    result=projection_compartments(edges)
    sums=result.groupby(['pre_type','post_type']).projection_fraction.sum().to_numpy()
    np.testing.assert_allclose(sums,1.)


def test_projection_contacts_are_repeated_total():
    edges=pd.DataFrame({'pre_type':['A','A'],'post_type':['B','B'],'neuropil':['PB','EB'],'syn_count':[3,2]})
    assert set(projection_compartments(edges).projection_contacts)=={5}
