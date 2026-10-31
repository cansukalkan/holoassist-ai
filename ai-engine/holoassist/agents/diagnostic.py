"""Deterministic diagnostic catalog evaluation for synthetic demo evidence only."""

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.diagnostic import DiagnosticCatalog, DiagnosticReport, SourceAssertion
from holoassist.rag.chunking import DocumentChunk


def matches(assertion: SourceAssertion, chunk: DocumentChunk) -> bool:
    return (
        chunk.document_id == assertion.document_id
        and chunk.document_version == assertion.document_version
        and chunk.checksum == assertion.checksum
        and (assertion.page is None or chunk.page == assertion.page)
        and (assertion.section is None or chunk.section == assertion.section)
        and assertion.quote in chunk.excerpt
    )


def evaluate_hypotheses(
    state: AnalysisState | Mapping, catalog: DiagnosticCatalog | Mapping
) -> DiagnosticReport:
    analysis = AnalysisState.model_validate(
        state.model_dump() if isinstance(state, AnalysisState) else state
    )
    rules = DiagnosticCatalog.model_validate(
        catalog.model_dump() if isinstance(catalog, DiagnosticCatalog) else catalog
    )
    base = dict(
        request_id=analysis.request.request_id,
        catalog_id=rules.catalog_id,
        catalog_version=rules.catalog_version,
    )
    if analysis.request.mode != "demo" or analysis.request.equipment_id != rules.equipment_id:
        return DiagnosticReport(**base, status="blocked", reason_code="catalog_context_mismatch")
    if analysis.status != "ready_for_diagnostic":
        return DiagnosticReport(**base, status="blocked", reason_code="analysis_not_ready")
    selected = [rule for rule in rules.rules if rule.symptom in analysis.request.symptom_codes]
    covered = {rule.symptom for rule in selected}
    missing = [
        f"catalog_for:{symptom}"
        for symptom in analysis.request.symptom_codes
        if symptom not in covered
    ]
    hypotheses = []
    citations = []
    for rule in selected:
        supporting = []
        contradicting = []
        for assertion in rule.assertions:
            found = sorted(
                (chunk for chunk in analysis.evidence if matches(assertion, chunk)),
                key=lambda item: item.evidence_id,
            )
            if not found:
                missing.append(f"source_for:{rule.code}:{assertion.assertion_id}")
            for chunk in found:
                target = supporting if assertion.relation == "supports" else contradicting
                target.append(chunk.evidence_id)
                citations.append(
                    dict(
                        rule_code=rule.code,
                        assertion_id=assertion.assertion_id,
                        evidence_id=chunk.evidence_id,
                        document_id=chunk.document_id,
                        document_version=chunk.document_version,
                        checksum=chunk.checksum,
                        page=chunk.page,
                        section=chunk.section,
                        relation=assertion.relation,
                        quote=assertion.quote,
                    )
                )
        if supporting:
            hypotheses.append(
                dict(
                    code=rule.code,
                    explanation=rule.explanation,
                    supporting_evidence_ids=tuple(sorted(set(supporting))),
                    contradicting_evidence_ids=tuple(sorted(set(contradicting))),
                    uncertainty="conflicting_evidence" if contradicting else "unverified",
                    missing_information=rule.missing_information,
                )
            )
    if missing:
        # Withhold all hypotheses if even a known contrary assertion was not retrieved.
        return DiagnosticReport(
            **base,
            status="needs_information",
            reason_code="catalog_evidence_incomplete",
            missing_information=tuple(sorted(set(missing))),
        )
    return DiagnosticReport(
        **base,
        status="hypotheses_available",
        reason_code="synthetic_catalog_evaluated",
        hypotheses=tuple(sorted(hypotheses, key=lambda item: item["code"])),
        assertion_matches=tuple(citations),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    args = parser.parse_args()
    try:

        def read(path: Path):
            with path.open("rb") as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("input exceeds 1 MiB")
            return json.loads(raw.decode("utf-8-sig"))

        result = evaluate_hypotheses(read(args.analysis), read(args.catalog))
    except (ValueError, OSError, TypeError):
        print("Diagnostic input rejected: invalid_or_unavailable_data", file=sys.stderr)
        return 2
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
