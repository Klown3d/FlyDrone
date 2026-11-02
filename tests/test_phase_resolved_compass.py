import numpy as np
import pandas as pd
from flydrone.neural.phase_resolved_compass import effective_transfer,projection_matrix


def test_effective_transfer_preserves_identity_path():
    inputs=np.eye(3);outputs=np.eye(3)
    np.testing.assert_allclose(effective_transfer(inputs,outputs),np.eye(3))


def test_effective_transfer_recovers_shifted_path():
    inputs=np.eye(3);outputs=np.roll(np.eye(3),1,axis=0)
    np.testing.assert_allclose(effective_transfer(inputs,outputs),outputs)


def test_projection_matrix_can_transfer_between_neuropils():
    nodes=pd.DataFrame([{'root_id':'cell','selected_type':'PEN','side':'left'}])
    phases=pd.Series({'epg0':0.,'epg1':1.})
    edges=pd.DataFrame([
        {'pre_pt_root_id':'epg0','post_pt_root_id':'cell','neuropil':'PB','syn_count':5},
        {'pre_pt_root_id':'cell','post_pt_root_id':'epg1','neuropil':'EB','syn_count':7},
        {'pre_pt_root_id':'epg1','post_pt_root_id':'cell','neuropil':'EB','syn_count':99},
    ])
    matrix,cells,input_contacts,output_contacts=projection_matrix(edges,nodes,phases,'PEN','PB','left','EB')
    assert cells==1 and input_contacts==5 and output_contacts==7
    np.testing.assert_allclose(matrix,np.array([[0.,0.],[1.,0.]]))
