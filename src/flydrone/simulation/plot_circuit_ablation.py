"""Create a compact figure from the completed 6DoF circuit ablation table."""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def run(root: Path) -> Path:
    folder=root/'results/simulation/quadrotor_circuit_ablation';frame=pd.read_csv(folder/'episodes.csv')
    frame['group']=frame['circuit_condition'].where(~frame['circuit_condition'].str.startswith('all_streams_row_shuffled'),'Barajado (5 grafos)')
    degree=pd.read_csv(root/'results/simulation/quadrotor_degree_preserving_null/episodes.csv');degree['group']='Grados preservados (5 grafos)';frame=pd.concat([frame,degree],ignore_index=True)
    order=['intact','Delta7_ablated','FC2_ablated','contact_multiplicity_uniformized','Barajado (5 grafos)','Grados preservados (5 grafos)','proportional']
    labels=['FlyWire\nintacto','Sin Δ7','Sin FC2','Topología\nbinaria','Barajado\npor fila','Grados\nfijos','Proporcional']
    grouped=frame.groupby('group').agg(episodes=('success','size'),success_rate=('success','mean'),median_progress=('normalized_terminal_progress','median'),median_efficiency=('path_efficiency','median')).reindex(order)
    colors=['#34d399','#fb7185','#fb7185','#fbbf24','#a78bfa','#8b5cf6','#60a5fa'];x=np.arange(len(order))
    figure,axes=plt.subplots(1,3,figsize=(15.5,4.5),constrained_layout=True)
    success=100*grouped.success_rate;axes[0].bar(x,success,color=colors);axes[0].set(ylabel='Éxito (%)',title='Llegada 6DoF',ylim=(0,110))
    axes[1].bar(x,100*grouped.median_progress,color=colors);axes[1].set(ylabel='Progreso terminal mediano (%)',title='Avance hacia la meta',ylim=(0,105))
    axes[2].bar(x,grouped.median_efficiency,color=colors);axes[2].set(ylabel='Distancia directa / recorrida',title='Eficiencia (sólo éxitos)',ylim=(0,1.05))
    for i,value in enumerate(success):axes[0].text(i,value+2,f'{value:.0f}%',ha='center',fontsize=8)
    for i,value in enumerate(grouped.median_efficiency):
        if pd.isna(value):axes[2].text(i,.03,'sin éxitos',ha='center',rotation=90,fontsize=7,color='.35')
    for axis in axes:
        axis.set_xticks(x,labels,fontsize=8);axis.grid(axis='y',alpha=.25);axis.set_axisbelow(True)
    figure.suptitle('Ablaciones computacionales del circuito en planta 6DoF',fontsize=13)
    output=folder/'circuit-ablation.png';figure.savefig(output,dpi=180);plt.close(figure);return output


if __name__=='__main__':run(Path.cwd())
