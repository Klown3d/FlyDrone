"""Publication-style diagnostic plot for representative 6-DoF traces."""
from pathlib import Path
import numpy as np
import yaml


def run(root: Path) -> Path:
    import matplotlib.pyplot as plt
    folder=root/'results/simulation/quadrotor_6dof';config=yaml.safe_load((root/'configs/quadrotor_benchmark.yaml').read_text())
    traces={}
    for label in ('neural','proportional'):
        data=np.load(folder/f'{label}-representative-trace.npz');columns=list(data['columns']);values=data['values']
        traces[label]={name:values[:,i] for i,name in enumerate(columns)}
    target_angle=np.deg2rad(config['target_bearings_deg'][0]);target=np.array([config['target_distance_m']*np.cos(target_angle),config['target_distance_m']*np.sin(target_angle)])
    colors={'neural':'#d946ef','proportional':'#22c55e'};labels={'neural':'FlyWire provisional','proportional':'Proporcional'}
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for key,trace in traces.items():
        axes[0,0].plot(trace['x_m'],trace['y_m'],color=colors[key],label=labels[key],lw=2)
        axes[0,1].plot(trace['time_s'],trace['z_m'],color=colors[key],label=labels[key])
        error=np.rad2deg(np.angle(np.exp(1j*(trace['yaw_rad']-trace['goal_rad']))))
        axes[1,0].plot(trace['time_s'],error,color=colors[key],label=labels[key])
        motor=np.column_stack([trace[f'motor_{i}_n'] for i in range(4)])
        axes[1,1].plot(trace['time_s'],motor.mean(axis=1),color=colors[key],label=labels[key])
    axes[0,0].scatter([0],[0],c='white',marker='o',label='Inicio');axes[0,0].scatter([target[0]],[target[1]],c='#fbbf24',marker='*',s=140,label='Meta')
    axes[0,0].set(xlabel='x (m)',ylabel='y (m)',title='Trayectoria horizontal');axes[0,0].axis('equal');axes[0,0].grid(alpha=.25);axes[0,0].legend(fontsize=8)
    axes[0,1].axhline(config['target_altitude_m'],color='#fbbf24',ls='--',lw=1);axes[0,1].set(xlabel='Tiempo (s)',ylabel='z (m)',title='Altura');axes[0,1].grid(alpha=.25)
    axes[1,0].axhline(0,color='gray',lw=1);axes[1,0].set(xlabel='Tiempo (s)',ylabel='Error heading-meta (°)',title='Alineación de yaw');axes[1,0].grid(alpha=.25)
    hover=yaml.safe_load((root/'configs/quadrotor.yaml').read_text())['mass_kg']*yaml.safe_load((root/'configs/quadrotor.yaml').read_text())['gravity_m_s2']/4
    axes[1,1].axhline(hover,color='#fbbf24',ls='--',lw=1,label='Hover teórico');axes[1,1].set(xlabel='Tiempo (s)',ylabel='Empuje medio por motor (N)',title='Carga de motores');axes[1,1].grid(alpha=.25);axes[1,1].legend(fontsize=8)
    fig.suptitle('FlyDrone — primera integración de waypoint con planta 6DoF',fontsize=14)
    output=folder/'representative-comparison.png';fig.savefig(output,dpi=180);plt.close(fig);return output


if __name__=='__main__':print(run(Path.cwd()))
