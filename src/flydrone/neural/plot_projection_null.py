"""Plot projection-specific degree-preserving heading nulls."""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def run(root: Path) -> Path:
    folder=root/'results/neural/projection_specific_degree_null';frame=pd.read_csv(folder/'summary.csv').set_index('projection')
    order=['epg_to_delta','delta_to_pfl3','fc2_weights'];labels=['EPG→Δ7','Δ7→PFL3','FC2→PFL3'];values=[100*frame.loc[key,'success_rate'] for key in order]
    figure,axis=plt.subplots(figsize=(7.2,4.2),constrained_layout=True);bars=axis.bar(labels,values,color=['#22c55e','#14b8a6','#38bdf8'])
    axis.set(title='Orientación tras reconfigurar una proyección',ylabel='Éxito en 80 episodios (%)',ylim=(0,15));axis.grid(axis='y',alpha=.25);axis.set_axisbelow(True)
    for bar,value in zip(bars,values):axis.text(bar.get_x()+bar.get_width()/2,value+.5,f'{value:.2f}%',ha='center')
    axis.text(.99,.97,'Intacto: 100%',transform=axis.transAxes,ha='right',va='top',fontsize=9,color='#047857')
    output=folder/'projection-null.png';figure.savefig(output,dpi=180);plt.close(figure);return output


if __name__=='__main__':run(Path.cwd())
