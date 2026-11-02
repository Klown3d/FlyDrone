"""Development comparison for graded PFN/hDeltaB drift confidence."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_oracle_diagnostics import trace_metrics
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.drift_confidence import DriftConfidenceGovernor
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator


def run(root:Path,config_path:Path=Path('configs/quadrotor_drift_confidence_development.yaml'))->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));base=yaml.safe_load((root/spec['base_config']).read_text(encoding='utf-8'));c={**base,**spec}
    plant=yaml.safe_load((root/c['plant_config']).read_text(encoding='utf-8'));orientation=yaml.safe_load((root/c['orientation_config']).read_text(encoding='utf-8'))
    model=EPGDelta7Candidate(root,root/orientation['candidate_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    output=root/c['output'];trace_dir=output/'traces';trace_dir.mkdir(parents=True,exist_ok=True);rows=[]
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                enabled=bool(condition['hdelta_enabled']);estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if enabled else None
                governor=DriftConfidenceGovernor(root/c['drift_confidence_config']) if condition['drift_confidence'] else None
                result,trace=simulate(root,local,plant,model,orientation,target,heading,condition['yaw_controller']=='proportional',enabled,scenario,int(scenario['seed'])+index,
                    heading_mode=condition['heading_mode'],compass_config=root/c['phase_compass_config'],controller_label=condition['name'],pfl2_enabled=False,
                    drift_controller=drift,drift_enabled=enabled,velocity_estimator=estimator,neural_advance_enabled=False,drift_confidence_governor=governor)
                row={**result}
                if enabled:
                    row.update(trace_metrics(trace,scenario,c));np.savez_compressed(trace_dir/f"{condition['name']}__{scenario['name']}__{index:02d}.npz",columns=np.asarray(trace['columns']),values=trace['values'])
                rows.append(row)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_decoded_direction_error_deg=('median_decoded_direction_error_deg','median'),median_recovery_time_s=('recovery_time_s','median'),mean_drift_confidence=('mean_drift_confidence','mean'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    by_scenario=frame.groupby(['controller','scenario'],as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'))
    report={'created_at':utc_now(),'status':'development_confidence_candidate','dataset':'FAFB','materialization_version':783,'claim':'First engineering confidence candidate after oracle/open-loop diagnosis; parameters are not prospectively validated and PFL2 is disabled.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'governor_source_sha256':file_hash(root/'src/flydrone/simulation/drift_confidence.py'),'episodes':len(frame),'summary':summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records'),'summary_by_scenario':by_scenario.astype(object).where(pd.notna(by_scenario),None).to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'development_confidence_candidate_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_drift_confidence_development.yaml'));run(Path.cwd(),parser.parse_args().config)
