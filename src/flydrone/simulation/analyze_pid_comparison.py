"""Pair the frozen PID/P results with matching intact-neural episodes."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now


KEYS=['scenario','target_bearing_deg','initial_relative_heading_deg']


def interval(values: np.ndarray,rng: np.random.Generator) -> tuple[float,float]:
    samples=rng.choice(values,(10000,len(values)),replace=True).mean(axis=1)
    return tuple(float(x) for x in np.quantile(samples,[.025,.975]))


def run(root: Path,config_path: Path=Path('configs/pid_comparison.yaml')) -> None:
    spec=yaml.safe_load((root/config_path).read_text());output=root/spec['output'];conventional=pd.read_csv(output/'held_out_episodes.csv')
    ideal=pd.read_csv(root/spec['neural_ideal_episodes']);ideal=ideal[(ideal.controller=='neural')&(ideal.circuit_condition=='intact')].copy();ideal['scenario']='ideal'
    robust=pd.read_csv(root/spec['neural_robustness_episodes']);robust=robust[(robust.controller=='neural')&(robust.circuit_condition=='intact')].copy()
    neural=pd.concat([ideal,robust],ignore_index=True);combined=pd.concat([conventional,neural],ignore_index=True)
    counts=combined.groupby(['scenario','controller']).size()
    if len(counts)!=9 or not (counts==16).all():raise ValueError(f'Expected 16 paired episodes in every block, got {counts.to_dict()}')
    if combined.duplicated(KEYS+['controller']).any():raise ValueError('Duplicate paired case')
    summary=combined.groupby(['scenario','controller']).agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_path_efficiency=('path_efficiency','median'),median_terminal_progress=('normalized_terminal_progress','median'),maximum_tilt_deg=('max_tilt_deg','max')).reset_index();summary.to_csv(output/'three_controller_summary.csv',index=False)
    wide=combined.pivot(index=KEYS,columns='controller',values='path_efficiency');rng=np.random.default_rng(20260922);rows=[]
    for scenario in ('ideal','combined_moderate','combined_strong'):
        block=wide.loc[scenario]
        for left,right in (('pid','neural'),('proportional','neural'),('pid','proportional')):
            difference=(block[left]-block[right]).to_numpy();low,high=interval(difference,rng)
            statistic,pvalue=wilcoxon(difference,alternative='two-sided',method='auto')
            rows.append({'scenario':scenario,'contrast':f'{left}_minus_{right}','paired_episodes':len(difference),'mean_path_efficiency_difference':float(difference.mean()),'median_path_efficiency_difference':float(np.median(difference)),'bootstrap_95pct_ci_mean_low':low,'bootstrap_95pct_ci_mean_high':high,'wilcoxon_statistic':float(statistic),'wilcoxon_two_sided_p_uncorrected':float(pvalue)})
    comparisons=pd.DataFrame(rows);comparisons.to_csv(output/'paired_path_efficiency.csv',index=False)
    report={'created_at':utc_now(),'claim':'Descriptive paired comparison on 16 deterministic held-out geometries per scenario; p-values are exploratory, uncorrected, and not evidence of biological superiority','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'pid_configuration':spec['pid_config'],'pid_configuration_sha256':file_hash(root/spec['pid_config']),'source_sha256':file_hash(Path(__file__)),'conventional_episodes_sha256':file_hash(output/'held_out_episodes.csv'),'neural_sources':{'ideal':{'path':spec['neural_ideal_episodes'],'sha256':file_hash(root/spec['neural_ideal_episodes'])},'robustness':{'path':spec['neural_robustness_episodes'],'sha256':file_hash(root/spec['neural_robustness_episodes'])}},'summary':summary.to_dict(orient='records'),'paired_path_efficiency':comparisons.to_dict(orient='records')};save_json(output/'comparison_report.json',report)
    pid_spec=yaml.safe_load((root/spec['pid_config']).read_text());manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));entry=manifest[pid_spec['manifest_key']];entry.update({'comparison_report':(output/'comparison_report.json').relative_to(root).as_posix(),'comparison_report_sha256':file_hash(output/'comparison_report.json'),'controllers_compared':['neural','pid','proportional'],'paired_cases_per_scenario':16});save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
