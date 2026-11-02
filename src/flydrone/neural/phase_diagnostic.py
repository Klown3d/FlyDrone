"""Contact phase identity, anatomical profiles, and controlled engineering ablations."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate, normalize_nonzero_rows
from flydrone.neural.evaluate_connectome import GOALS_DEG, RELATIVE_HEADINGS_DEG


def circular_summary(weights: np.ndarray, angles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = normalize_nonzero_rows(weights) @ np.exp(1j * angles)
    return np.angle(z), np.abs(z)


def continuous_epg_angles(candidate: EPGDelta7Candidate, synapses: pd.DataFrame) -> np.ndarray:
    """Project EPG contact centroids onto provisional PB anchor polyline.

    Uses anatomy only; no PFL3 target/readout optimization. Anchor labels remain
    inferred from skeleton geometry, so this is not independent glomerular truth.
    """
    columns = ['PB_median_x_nm', 'PB_median_y_nm', 'PB_median_z_nm']
    anchors = candidate.epg.groupby('geometric_column')[columns].mean().sort_index()
    xyz = anchors.to_numpy()
    phases = np.unwrap(np.deg2rad([candidate.config['epg_preferred_heading_deg'][c] for c in anchors.index]))
    contacts = synapses.loc[synapses.pre_pt_root_id.astype(str).isin(candidate.epg_ids)]
    centers = contacts.groupby('pre_pt_root_id')[[f'pre_pt_position_{a}' for a in 'xyz']].mean()
    results = []
    for root_id in candidate.epg_ids:
        if int(root_id) not in centers.index:
            raise ValueError(f'No PB output contacts for EPG {root_id}')
        point = centers.loc[int(root_id)].to_numpy()
        segments = xyz[1:] - xyz[:-1]
        fraction = np.clip(np.sum((point - xyz[:-1]) * segments, axis=1) / np.sum(segments**2, axis=1), 0, 1)
        projected = xyz[:-1] + fraction[:, None] * segments
        best = np.argmin(np.sum((point - projected)**2, axis=1))
        results.append(phases[best] + fraction[best] * (phases[best+1] - phases[best]))
    return np.asarray(results)


def stable_crossing(x: np.ndarray, y: np.ndarray) -> float | None:
    roots = []
    for i in range(len(x)-1):
        if y[i+1] >= y[i]:
            continue
        if y[i] == 0 or y[i] * y[i+1] < 0:
            roots.append(float(x[i] - y[i] * (x[i+1]-x[i]) / (y[i+1]-y[i])))
    return min(roots, key=abs) if roots else None


def run(root: Path) -> None:
    config_path = root / 'configs/phase_diagnostic.yaml'
    config = yaml.safe_load(config_path.read_text())
    model = EPGDelta7Candidate(root, root / config['candidate_config'])
    synapses = pd.read_parquet(root / config['synapses'])
    provenance = json.loads((root / config['synapses']).with_suffix('.provenance.json').read_text())
    if provenance['pair_count_mismatches'] or provenance['rows'] != provenance['unique_synapse_ids']:
        raise ValueError('Synapse extraction validation failed; inspect count discrepancies')
    output = root / config['output']
    output.mkdir(parents=True, exist_ok=True)
    old = model.epg_angles_rad
    continuous = continuous_epg_angles(model, synapses)
    phase, resultant = circular_summary(model.epg_to_delta_raw, old)
    heading = np.deg2rad(GOALS_DEG[:, None] + RELATIVE_HEADINGS_DEG[None, :]).reshape(-1)
    goal = np.repeat(np.deg2rad(GOALS_DEG), len(RELATIVE_HEADINGS_DEG))
    direct = np.cos(heading[:, None]-old) @ model.epg_to_delta.T
    reconstructed = resultant * np.cos(heading[:, None]-phase)
    identity_error = float(np.max(np.abs(direct-reconstructed)))
    if identity_error > config['phase_resultant_tolerance']:
        raise AssertionError('Circular phase identity failed')
    cp, cr = circular_summary(model.epg_to_delta_raw, continuous)
    pd.DataFrame({'root_id': model.base.delta_ids, 'contact_phase_deg': np.rad2deg(phase),
                  'resultant': resultant, 'continuous_contact_phase_deg': np.rad2deg(cp),
                  'continuous_resultant': cr,
                  'phase_defined': resultant > config['phase_resultant_tolerance']}).to_csv(output/'delta7-contact-phases.csv', index=False)
    model.epg.assign(continuous_phase_deg=np.rad2deg(continuous)).to_csv(output/'epg-continuous-phases.csv', index=False)
    # Classify contact positions against provisional EPG PB anchors, not cell-type sublabels.
    anchors = model.epg.groupby('geometric_column')[['PB_median_x_nm','PB_median_y_nm','PB_median_z_nm']].mean().sort_index()
    profiles = []
    for direction, endpoint, position in [('input','post_pt_root_id','post'), ('output','pre_pt_root_id','pre')]:
        contacts = synapses.loc[synapses[endpoint].astype(str).isin(model.base.delta_ids)].copy()
        points = contacts[[f'{position}_pt_position_{a}' for a in 'xyz']].to_numpy()
        labels = np.argmin(((points[:, None, :]-anchors.to_numpy()[None, :, :])**2).sum(axis=2), axis=1)
        contacts['provisional_glomerulus'] = anchors.index.to_numpy()[labels]
        counts = contacts.groupby([endpoint, 'provisional_glomerulus']).size().reset_index(name='contacts').rename(columns={endpoint:'root_id'})
        counts['direction'] = direction
        profiles.append(counts)
    pd.concat(profiles).to_csv(output/'delta7-glomerular-contact-profiles.csv', index=False)
    recurrence = normalize_nonzero_rows(model.delta_to_delta_raw)
    system = np.eye(len(recurrence)) + config['recurrence_gain'] * recurrence
    stability_margin = float(np.min(np.real(np.linalg.eigvals(system))))
    conditions = [
        ('old_binning_linear', old, False, False, False),
        ('circular_equivalent', old, False, False, True),
        ('continuous_anatomical_phase', continuous, False, False, False),
        ('continuous_with_recurrence', continuous, True, False, False),
        ('continuous_with_sigmoid', continuous, False, True, False),
        ('old_reflected_convention_diagnostic', -old, False, False, False),
        ('continuous_reflected_convention_diagnostic', -continuous, False, False, False),
        ('continuous_reflected_with_recurrence', -continuous, True, False, False),
        ('continuous_reflected_with_sigmoid', -continuous, False, True, False),
    ]
    reports = []
    p = model.base.parameters
    goal_drive = np.cos(goal[:, None]-model.base.fc2_angles_rad) @ model.base.fc2_weights.T
    for name, angles, recurrent, sigmoid, circular in conditions:
        epg = np.cos(heading[:, None]-angles)
        delta = reconstructed.copy() if circular else epg @ model.epg_to_delta.T
        if recurrent:
            if stability_margin <= 0:
                raise ValueError('Linear recurrence has no asymptotically stable fixed point')
            delta = np.linalg.solve(system, delta.T).T
        if sigmoid:
            # Centered logistic 2*sigmoid(2*slope*x)-1; signed deviation, not firing Hz.
            delta = np.tanh(config['sigmoid_slope'] * delta)
        drive = -delta @ model.delta_to_pfl3.T + p.goal_input_gain_d * goal_drive
        rates = p.output_scale_hz_a * np.logaddexp(0, p.softplus_slope_b*(drive+p.input_offset_c))
        signals = np.array([model.base.readout(r) for r in rates]).reshape(len(GOALS_DEG), -1)
        roots = [stable_crossing(RELATIVE_HEADINGS_DEG, s) for s in signals]
        errors = [abs(r) for r in roots if r is not None]
        mask = (np.abs(RELATIVE_HEADINGS_DEG)>=5)&(np.abs(RELATIVE_HEADINGS_DEG)<=170)
        accuracy = float(np.mean(np.sign(signals[:, mask]) == -np.sign(RELATIVE_HEADINGS_DEG[mask])))
        trace = pd.DataFrame({'goal_deg': np.rad2deg(goal), 'heading_deg':np.rad2deg(heading), 'right_minus_left_hz':signals.reshape(-1)})
        for i, rid in enumerate(model.base.pfl3.root_id):
            trace[f'rate_hz_{rid}'] = rates[:, i]
        neural_path = output/f'{name}-delta7-deviations.csv'
        pd.DataFrame(delta, columns=model.base.delta_ids).to_csv(neural_path, index=False)
        path = output/f'{name}-trace.csv'
        trace.to_csv(path, index=False)
        reports.append({'condition':name, 'mean_abs_stable_equilibrium_error_deg':float(np.mean(errors)) if errors else None,
                        'goals_with_stable_equilibrium':len(errors), 'direction_accuracy':accuracy,
                        'trace_sha256':file_hash(path), 'delta7_deviations_sha256':file_hash(neural_path)})
    phase_audits = []
    for label, angles in [('old', old), ('continuous',continuous), ('old_reflected',-old), ('continuous_reflected',-continuous)]:
        model.epg_angles_rad = angles
        fit = model.phase_fit('via_delta7')
        phase_audits.append({'condition':label, 'offset_deg':fit['phase_offset_deg'], 'mean_abs_residual_deg':fit['mean_abs_residual_deg']})
    save_json(output/'report.json', {'created_at':utc_now(), 'dataset':'FAFB', 'materialization_version':783,
        'claim':'Diagnostic only; provisional anatomical anchors, no functional validation',
        'circular_identity_max_abs_error':identity_error,
        'recurrence_linear_stability_margin_dimensionless':stability_margin,
        'recurrence_model':'Exact steady state of tau*dx/dt=-x+EPG_input-gain*rownorm(DD)*x; tau unspecified, no transient claim',
        'area_weight_condition':'unavailable: table has no area; confidence scores are not area',
        'phase_calibration':'No fitted offset used for steering; reflection conditions explicitly reverse EPG angles only',
        'config_sha256':file_hash(config_path), 'synapses_sha256':file_hash(root/config['synapses']),
        'phase_audits_global_fit_diagnostic_only':phase_audits, 'conditions':reports})
    manifest_path = root / 'data/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['status'] = 'phase_convention_diagnostic_promising_pending_full_glomerular_validation'
    manifest.setdefault('neural_model', {})['phase_diagnostic'] = {
        'status': 'diagnostic_only_not_promoted_to_controller',
        'report': (output/'report.json').relative_to(root).as_posix(),
        'report_sha256':file_hash(output/'report.json'),
        'config': config_path.relative_to(root).as_posix(),
        'config_sha256':file_hash(config_path),
        'source_code_sha256':file_hash(Path(__file__)),
    }
    manifest['selected_pb_synapse_extraction'] = {
        'dataset':'FAFB', 'materialization_version':783,
        'path':config['synapses'], 'sha256':file_hash(root/config['synapses']),
        'rows':provenance['rows'], 'pair_count_mismatches':provenance['pair_count_mismatches'],
        'provenance':(root/config['synapses']).with_suffix('.provenance.json').relative_to(root).as_posix(),
    }
    save_json(manifest_path, manifest)
    print(reports, flush=True)


if __name__ == '__main__':
    run(Path.cwd())
