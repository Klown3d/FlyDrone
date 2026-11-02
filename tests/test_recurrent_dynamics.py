import numpy as np
import pandas as pd
from flydrone.neural.recurrent_dynamics import normalized_signed_matrix,readout


def test_delta7_presynaptic_columns_are_inhibitory():
    nodes=pd.DataFrame({'root_id':['e','d'],'selected_type':['EPG','Delta7']})
    edges=pd.DataFrame({'pre_pt_root_id':['e','d'],'post_pt_root_id':['e','e'],'syn_count':[2,1]})
    matrix=normalized_signed_matrix(nodes,edges)
    assert matrix[0,0]>0 and matrix[0,1]<0
    assert np.isclose(np.abs(matrix[0]).sum(),1)


def test_population_readout_recovers_active_phase():
    state=np.array([[0.,1.,0.]])
    phase,resultant,contrast=readout(state,np.array([0,1,2]),np.deg2rad([0,90,180]))
    assert np.isclose(np.rad2deg(phase[0]),90)
    assert np.isclose(resultant[0],1) and np.isclose(contrast[0],1)


def test_compartment_gate_keeps_delta_pb_and_pen_no():
    nodes=pd.DataFrame({'root_id':['e','d','p'],'selected_type':['EPG','Delta7','PEN_a(PEN1)']})
    edges=pd.DataFrame({'pre_pt_root_id':['d','d','p','p'],'post_pt_root_id':['e','e','p','e'],'neuropil':['PB','EB','NO','EB'],'syn_count':[2,9,3,4]})
    matrix=normalized_signed_matrix(nodes,edges,True)
    assert matrix[0,1]<0 and matrix[1].sum()==0 and matrix[2,2]>0 and matrix[0,2]>0
