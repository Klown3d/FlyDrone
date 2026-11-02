"""Plot the preserved obstacle-planner experiments without rerunning them."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def run(root: Path) -> Path:
    experiments=[
        ("v1: lado fijo\ncasos de desarrollo",root/"results/simulation/quadrotor_6dof_obstacles/summary.csv","conventional_safety_planner"),
        ("v2: punto retenido\ncasos de desarrollo",root/"results/simulation/quadrotor_6dof_obstacles_v2_diagnostic/summary.csv","conventional_safety_planner_v2_diagnostic"),
        ("v3: lado según rumbo\ncasos no usados",root/"results/simulation/quadrotor_6dof_obstacles_v3_held_out/summary.csv","heading_aware_safety_planner_v3_held_out"),
    ]
    rows=[]
    for stage,path,scenario in experiments:
        frame=pd.read_csv(path)
        for _,row in frame[frame.scenario==scenario].iterrows():
            rows.append({"stage":stage,**row.to_dict()})
    data=pd.DataFrame(rows);controllers=["neural","proportional"];colors={"neural":"#34d399","proportional":"#60a5fa"}
    figure,axes=plt.subplots(1,3,figsize=(13,4.4),constrained_layout=True)
    x=range(len(experiments));width=.34
    for offset,controller in zip((-.17,.17),controllers):
        subset=data[data.controller==controller].set_index("stage")
        ordered=[subset.loc[label] for label,_,_ in experiments]
        axes[0].bar([i+offset for i in x],[100*r.successes/r.episodes for r in ordered],width,label="FlyWire provisional" if controller=="neural" else "Proporcional",color=colors[controller])
        axes[1].bar([i+offset for i in x],[r.collisions for r in ordered],width,color=colors[controller])
        axes[2].bar([i+offset for i in x],[r.median_path_efficiency for r in ordered],width,color=colors[controller])
    labels=[label for label,_,_ in experiments]
    for axis in axes:
        axis.set_xticks(list(x),labels,fontsize=8);axis.grid(axis="y",alpha=.25);axis.set_axisbelow(True)
    axes[0].set(title="Llegadas",ylabel="Éxito (%)",ylim=(0,105));axes[0].legend(frameon=False,fontsize=8)
    axes[1].set(title="Colisiones",ylabel="Episodios",ylim=(0,9))
    axes[2].set(title="Eficiencia de trayectoria",ylabel="Distancia directa / recorrida",ylim=(0,1))
    figure.suptitle("Evolución de la capa convencional de evasión en planta 6DoF",fontsize=13)
    output=root/"results/simulation/quadrotor_6dof_obstacles_v3_held_out/obstacle-progression.png"
    figure.savefig(output,dpi=180);plt.close(figure);return output


if __name__=="__main__":
    run(Path.cwd())
