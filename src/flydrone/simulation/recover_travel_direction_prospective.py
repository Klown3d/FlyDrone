"""Recover the frozen report from the already-completed 120-episode CSV."""
from pathlib import Path
import json
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash, save_json, utc_now

ROOT=Path.cwd(); config_path=Path("configs/quadrotor_travel_direction_prospective.yaml")
c=yaml.safe_load((ROOT/config_path).read_text(encoding="utf-8")); output=ROOT/c["output"]
report_path=output/"report.json"
if report_path.exists(): raise RuntimeError(f"Prospective report already exists: {report_path}")
frame=pd.read_csv(output/"episodes.csv")
if len(frame)!=120: raise RuntimeError(f"Expected 120 frozen episodes, found {len(frame)}")
summary=frame.groupby("controller",as_index=False).agg(episodes=("success","size"),successes=("success","sum"),median_maximum_cross_track_m=("maximum_absolute_cross_track_m","median"),median_mean_cross_track_m=("mean_absolute_cross_track_m","median"),median_arrival_time_s=("arrival_time_s","median"),median_path_efficiency=("path_efficiency","median"),maximum_motor_saturation_fraction=("motor_saturation_fraction","max"))
s=summary.set_index("controller");h=s.loc["hdelta_compensation"];a=s.loc["no_drift_compensation"];v=s.loc["conventional_velocity_compensation"];n=s.loc["shuffled_pfn_phases"];g=c["gate"]
effects={"success_advantage_over_absent":int(h.successes-a.successes),"cross_track_reduction_vs_absent_fraction":float(1-h.median_maximum_cross_track_m/a.median_maximum_cross_track_m),"cross_track_disadvantage_vs_conventional_m":float(h.median_maximum_cross_track_m-v.median_maximum_cross_track_m),"cross_track_reduction_vs_shuffled_fraction":float(1-h.median_maximum_cross_track_m/n.median_maximum_cross_track_m)}
criteria={"hdelta_successes":bool(h.successes>=g["minimum_hdelta_successes"]),"success_advantage":bool(effects["success_advantage_over_absent"]>=g["minimum_success_advantage_over_absent"]),"reduction_vs_absent":bool(effects["cross_track_reduction_vs_absent_fraction"]>=g["minimum_cross_track_reduction_vs_absent_fraction"]),"bounded_vs_conventional":bool(effects["cross_track_disadvantage_vs_conventional_m"]<=g["maximum_cross_track_disadvantage_vs_conventional_m"]),"reduction_vs_shuffled":bool(effects["cross_track_reduction_vs_shuffled_fraction"]>=g["minimum_cross_track_reduction_vs_shuffled_fraction"]),"motor_saturation":bool(h.maximum_motor_saturation_fraction<=g["maximum_motor_saturation_fraction"])}
report={"created_at":utc_now(),"status":"immutable_run_once_prospective_result_recovered_from_frozen_csv","recovery_reason":"All flights completed; original writer failed on numpy.bool JSON serialization before metrics were printed.","dataset":"FAFB","materialization_version":783,"claim":"Prospective paired 6DoF drift gate; neural direction with engineering speed magnitude and inner loop.","configuration":config_path.as_posix(),"configuration_sha256":file_hash(ROOT/config_path),"frozen_executor_sha256":"1cbe43314503e990024d39838e1c87e8825d4c39c73a581a9f6a48fe3b9dfc26","recovery_source_sha256":file_hash(Path(__file__)),"episodes_csv_sha256":file_hash(output/"episodes.csv"),"episodes":len(frame),"effects":effects,"criteria":criteria,"passes_prospective_gate":all(criteria.values()),"summary":summary.to_dict(orient="records")}
save_json(report_path,report);manifest_path=ROOT/"data/manifest.json";manifest=json.loads(manifest_path.read_text(encoding="utf-8"));manifest[c["manifest_key"]]={"status":"prospective_gate_completed_recovered_report","report":report_path.relative_to(ROOT).as_posix(),"report_sha256":file_hash(report_path),"passed":report["passes_prospective_gate"]};save_json(manifest_path,manifest)
print(json.dumps(report,indent=2),flush=True)
