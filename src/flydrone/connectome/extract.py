"""Extract a deterministic induced graph and its one-hop boundary from FAFB."""
from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now, verify

PRE, POST, COUNT = "pre_pt_root_id", "post_pt_root_id", "syn_count"
NT = ["gaba_avg", "ach_avg", "glut_avg", "oct_avg", "ser_avg", "da_avg"]


def load_annotations(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = reader.fieldnames or []
        if not {"root_id", "hemibrain_type", "side", "cell_type", "status"} <= set(fields):
            raise ValueError("Missing annotation columns")
        result = {}
        for row in reader:
            rid = str(int(row["root_id"]))
            if rid in result:
                raise ValueError(f"Duplicate annotation root ID: {rid}")
            result[rid] = row
        return result, fields


def select_nodes(annotations: dict[str, dict[str, str]], config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Exact matching; retain original subtype and unresolved functional mapping."""
    result = {}
    for rid, row in annotations.items():
        label = row[config["type_column"]]
        if label in config["types"]:
            result[rid] = {**row, "selected_type": label, "family": config["types"][label],
                           "selection_basis": config["type_column"],
                           "functional_column": "unresolved", "preferred_angle_rad": "",
                           "functional_sign": "unresolved"}
    counts = Counter(r["selected_type"] for r in result.values())
    if missing := set(config["types"]) - set(counts):
        raise ValueError(f"Requested labels absent: {sorted(missing)}")
    return dict(sorted(result.items(), key=lambda item: int(item[0])))


def aggregate_pairs(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Sum disjoint neuropil rows exactly once, reject duplicate region keys."""
    totals: dict[tuple[str, str], int] = defaultdict(int)
    seen = set()
    for row in rows:
        a, b, region = str(row[PRE]), str(row[POST]), row["neuropil"]
        key = (a, b, region)
        if key in seen:
            raise ValueError(f"Duplicate pair/neuropil: {key}")
        seen.add(key)
        n = row[COUNT]
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ValueError("Synapse counts must be positive integers")
        totals[(a, b)] += n
    return dict(sorted(totals.items(), key=lambda item: (int(item[0][0]), int(item[0][1]))))


def graph_stats(nodes: list[str], pairs: dict[tuple[str, str], int], threshold: int) -> dict[str, Any]:
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from((a, b, n) for (a, b), n in pairs.items() if n >= threshold)
    components = lambda groups: sorted([sorted(c, key=int) for c in groups], key=lambda c: (-len(c), c))
    reciprocal = sorted((a, b) for a, b in graph.edges if int(a) < int(b) and graph.has_edge(b, a))
    return {"threshold": threshold, "nodes": len(graph), "edges": graph.number_of_edges(),
            "synapses": sum(n for n in pairs.values() if n >= threshold),
            "weak_components": components(nx.weakly_connected_components(graph)),
            "strong_components": components(nx.strongly_connected_components(graph)),
            "isolates": sorted(nx.isolates(graph), key=int),
            "self_loops": sorted(nx.nodes_with_selfloops(graph), key=int),
            "reciprocal_pairs_count": len(reciprocal), "reciprocal_pairs": reciprocal,
            "in_degree_histogram": dict(sorted(Counter(dict(graph.in_degree()).values()).items())),
            "out_degree_histogram": dict(sorted(Counter(dict(graph.out_degree()).values()).items())),
            "per_node": {n: {"in_degree": graph.in_degree(n), "out_degree": graph.out_degree(n),
                               "in_strength": graph.in_degree(n, weight="weight"),
                               "out_strength": graph.out_degree(n, weight="weight")} for n in nodes}}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def extract(root: Path, config_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset = manifest["dataset"]
    if config["materialization_version"] != dataset["materialization_version"] or config["annotation_commit"] != dataset["annotation_commit"] or config["dataset"] != dataset["specimen_dataset"]:
        raise ValueError("Configuration/data version mismatch")
    if config["neuropil_filter"] is not None or config["boundary_hops"] != 1:
        raise ValueError("This extractor supports all neuropils and one-hop boundary only")
    thresholds = [config["minimum_pair_synapses"], *config["sensitivity_thresholds"]]
    if any(type(t) is not int or t < 1 for t in thresholds):
        raise ValueError("Thresholds must be positive integers")
    paths = {}
    for artifact in manifest["artifacts"]:
        if artifact["status"] != "downloaded_verified":
            raise ValueError("Complete acquisition before extraction")
        path = root / artifact["local_path"]
        if verify(path, artifact) != artifact["local_sha256"]:
            raise ValueError("Local SHA-256 mismatch")
        paths[artifact["name"]] = path
    annotations, annotation_fields = load_annotations(paths["Supplemental_file1_neuron_annotations.tsv"])
    selected = select_nodes(annotations, config)
    proofread_array = np.load(paths["proofread_root_ids_783.npy"], allow_pickle=False)
    if proofread_array.ndim != 1 or proofread_array.dtype.kind not in "iu":
        raise ValueError("Unexpected proofread ID array")
    proofread = {str(int(r)) for r in proofread_array}
    if len(proofread) != len(proofread_array) or not set(selected) <= proofread:
        raise ValueError("Duplicate proofread IDs or selected non-proofread cells")
    print(f"Selected {len(selected)} neurons; reading connectivity", flush=True)
    table = feather.read_table(paths["proofread_connections_783.feather"], memory_map=True)
    columns = [PRE, POST, "neuropil", COUNT] + NT
    if not set(columns) <= set(table.column_names):
        raise ValueError(f"Unexpected connectivity columns: {table.column_names}")
    schema_text = str(table.schema)
    table = table.select(columns)
    for name in (PRE, POST, COUNT):
        if not pa.types.is_integer(table.schema.field(name).type):
            raise ValueError(f"Non-integer {name}")
    id_values = pa.array([int(r) for r in selected], type=table.schema.field(PRE).type)
    relevant = []
    for batch in table.to_batches(max_chunksize=262144):
        chunk = pa.Table.from_batches([batch])
        if any(chunk[n].null_count for n in (PRE, POST, COUNT)):
            raise ValueError("Null endpoint/count in source connectivity")
        mask = pc.or_(pc.is_in(chunk[PRE], value_set=id_values), pc.is_in(chunk[POST], value_set=id_values))
        relevant.extend(chunk.filter(mask).to_pylist())
    source_rows = len(table)
    del table
    relevant.sort(key=lambda r: (r[PRE], r[POST], str(r["neuropil"])))
    for row in relevant:
        row[PRE], row[POST] = str(row[PRE]), str(row[POST])
        if not row["neuropil"]:
            row["neuropil"] = "UNASSIGNED"
        if row[PRE] not in proofread or row[POST] not in proofread:
            raise ValueError("Relevant edge endpoint not in proofread set")
        for key in NT:
            value = row[key]
            if value is not None and not (0 <= value <= 1):
                raise ValueError("Invalid neurotransmitter probability")
    all_pairs = aggregate_pairs(relevant)
    inside = [r for r in relevant if r[PRE] in selected and r[POST] in selected]
    pairs = aggregate_pairs(inside)
    threshold = config["minimum_pair_synapses"]
    keep = {p for p, n in pairs.items() if n >= threshold}
    inside = [r for r in inside if (r[PRE], r[POST]) in keep]
    boundary = [{**r, "direction": "outgoing" if r[PRE] in selected else "incoming"}
                for r in relevant if (r[PRE] in selected) != (r[POST] in selected)]
    total_in, total_out, internal_in, internal_out = (Counter() for _ in range(4))
    lal = defaultdict(Counter)
    for (a, b), n in all_pairs.items():
        if a in selected:
            total_out[a] += n
        if b in selected:
            total_in[b] += n
    for (a, b), n in pairs.items():
        if (a, b) in keep:
            internal_out[a] += n
            internal_in[b] += n
    for r in relevant:
        if r[PRE] in selected and r["neuropil"] in ("LAL_L", "LAL_R"):
            lal[r[PRE]][r["neuropil"]] += r[COUNT]
    degrees = graph_stats(list(selected), pairs, threshold)
    nodes = []
    for rid, annotation in selected.items():
        l, r = lal[rid]["LAL_L"], lal[rid]["LAL_R"]
        side = "left" if l > r else "right" if r > l else "unresolved"
        nodes.append({**annotation, **degrees["per_node"][rid],
            "proofread": True, "total_input_synapses_proofread": total_in[rid],
            "total_output_synapses_proofread": total_out[rid],
            "excluded_input_fraction": 1 - internal_in[rid] / total_in[rid] if total_in[rid] else None,
            "excluded_output_fraction": 1 - internal_out[rid] / total_out[rid] if total_out[rid] else None,
            "output_contacts_LAL_L": l, "output_contacts_LAL_R": r,
            "dominant_LAL_contact_side": side,
            "LAL_side_basis": "synapse locations only; functional turning sign unresolved"})
    class_pairs = defaultdict(lambda: {"edges": 0, "synapses": 0})
    for (a, b), n in pairs.items():
        if (a, b) in keep:
            entry = class_pairs[(selected[a]["selected_type"], selected[b]["selected_type"])]
            entry["edges"] += 1
            entry["synapses"] += n
    class_rows = [{"pre_type": a, "post_type": b, **v} for (a, b), v in sorted(class_pairs.items())]
    strongest = [{"pre_root_id": a, "post_root_id": b, "syn_count": n,
                  "pre_type": selected[a]["selected_type"], "post_type": selected[b]["selected_type"]}
                 for (a, b), n in sorted(pairs.items(), key=lambda x: (-x[1], x[0]))[:30]]
    external_ids = sorted(({r[PRE] for r in boundary} | {r[POST] for r in boundary}) - set(selected), key=int)
    boundary_nodes = [{"root_id": rid, "annotation_available": rid in annotations,
                       **{k: annotations.get(rid, {}).get(k, "") for k in ("cell_type", "hemibrain_type", "side", "status")}}
                      for rid in external_ids]
    outputs = (root / config["output_dir"]).resolve()
    if not outputs.is_relative_to(root.resolve() / "data/processed"):
        raise ValueError("Output must remain under data/processed")
    outputs.mkdir(parents=True, exist_ok=True)
    write_csv(outputs / "nodes.csv", nodes, list(nodes[0]))
    write_csv(outputs / "edges.csv", inside, columns)
    pair_rows = [{PRE: a, POST: b, COUNT: n} for (a, b), n in pairs.items() if (a, b) in keep]
    write_csv(outputs / "edges_by_pair.csv", pair_rows, [PRE, POST, COUNT])
    write_csv(outputs / "boundary_edges.csv", boundary, columns + ["direction"])
    write_csv(outputs / "boundary_nodes.csv", boundary_nodes, list(boundary_nodes[0]) if boundary_nodes else ["root_id"])
    write_csv(outputs / "class_connectivity.csv", class_rows, ["pre_type", "post_type", "edges", "synapses"])
    mapping = [{"root_id": r["root_id"], "source_label": r["selected_type"], "family": r["family"],
                "source_column": config["type_column"], "functional_column": "unresolved",
                "preferred_angle_rad": "", "functional_transfer_to_subtype": "unvalidated"} for r in nodes]
    write_csv(outputs / "type_mapping.csv", mapping, list(mapping[0]))
    report = {"dataset": dataset, "configuration": config, "config_sha256": file_hash(config_path),
        "source_rows": source_rows, "relevant_region_rows": len(relevant),
        "annotation_rows": len(annotations), "proofread_ids": len(proofread),
        "annotation_columns": annotation_fields, "connectivity_schema": schema_text,
        "selected_by_type": dict(sorted(Counter(r["selected_type"] for r in nodes).items())),
        "selected_by_type_soma_side": dict(sorted(Counter(r["selected_type"] + ":" + r["side"] for r in nodes).items())),
        "related_excluded": {t: sum(r[config["type_column"]] == t for r in annotations.values()) for t in config["excluded_related_types"]},
        "graph": degrees, "internal_region_rows": len(inside),
        "internal_synapses_by_neuropil": dict(sorted(Counter({region: sum(r[COUNT] for r in inside if r['neuropil'] == region) for region in {r['neuropil'] for r in inside}}).items())),
        "boundary_region_rows": len(boundary), "external_neurons": len(external_ids),
        "boundary_missing_annotations": sum(r not in annotations for r in external_ids),
        "boundary_synapses": dict(sorted(Counter({d: sum(r[COUNT] for r in boundary if r['direction'] == d) for d in ['incoming', 'outgoing']}).items())),
        "class_connectivity": class_rows, "strongest_pairs": strongest,
        "threshold_sensitivity": [graph_stats(list(selected), pairs, t) for t in config["sensitivity_thresholds"]],
        "annotation_quality_flags": [r for r in nodes if r["status"]],
        "neurotransmitter_predictions_by_type": dict(sorted(Counter(r["selected_type"] + ":" + r["top_nt"] for r in nodes).items())),
        "functional_model_ready": False,
        "limitations": ["Column/preferred-angle mapping unresolved.", "Transmitter predictions are not signed physiological weights.",
                         "Boundary denominators include proofread partners only; missing non-proofread contacts not quantified.",
                         "Soma side and dominant LAL contact side are different measures; neither establishes functional turning sign.",
                         "FC2 subtype functional equivalence not established; no missing connections were added."]}
    save_json(outputs / "circuit-report.json", report)
    artifacts = []
    for p in sorted(outputs.iterdir()):
        if p.suffix in (".csv", ".json") and p.name != "provenance.json" and not p.name.endswith(".metadata.json"):
            artifacts.append({"path": p.relative_to(root).as_posix(), "sha256": file_hash(p), "bytes": p.stat().st_size})
    provenance = {"dataset": dataset, "extracted_at": utc_now(), "config_sha256": file_hash(config_path),
                  "python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pyarrow", "networkx", "PyYAML"]},
                  "git_commit": None, "source_code_sha256": {p.relative_to(root).as_posix(): file_hash(p) for p in sorted((root / 'src').rglob('*.py'))},
                  "sources": manifest["artifacts"], "citations": manifest["required_citations"], "outputs": artifacts}
    save_json(outputs / "provenance.json", provenance)
    # Each export has a colocated metadata pointer; provenance includes its hash,
    # dataset, source retrieval dates, source hashes and citations.
    for artifact in artifacts:
        path = root / artifact["path"]
        save_json(path.with_suffix(path.suffix + ".metadata.json"), {"provenance": "provenance.json", "dataset": dataset,
                  "sha256": artifact["sha256"], "source_retrieved_at": {a['name']: a['retrieved_at'] for a in manifest['artifacts']},
                  "citations": manifest["required_citations"]})
    extraction_record={"output_dir": config["output_dir"], "config_sha256": file_hash(config_path),
                       "provenance": (outputs / 'provenance.json').relative_to(root).as_posix(),
                       "neuron_count": len(selected), "edge_count": degrees["edges"]}
    if config.get("register_as_primary", True):
        manifest.update(phase="2_circuit_extraction", status="anatomy_extracted_functional_mapping_pending",
                        selection_status="anatomical_extraction_complete_functional_audit_pending",
                        cell_ids=list(selected), neuron_count=len(selected), edge_count=degrees["edges"],
                        extraction=extraction_record)
    else:
        key=config.get("manifest_key")
        if not key:raise ValueError("Secondary extraction requires manifest_key")
        manifest.setdefault("additional_extractions", {})[key]=extraction_record
    save_json(manifest_path, manifest)
    print(json.dumps({"counts": report["selected_by_type"], "edges": degrees["edges"], "synapses": degrees["synapses"], "boundary_rows": len(boundary)}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/data.yaml"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    extract(args.root.resolve(), args.config.resolve())
