"""Source-bound diagnostic demo contracts; no intervention permissions."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.analysis import Symptom
from holoassist.contracts.models import Checksum, Contract, NonBlank


class SourceAssertion(Contract):
    assertion_id: NonBlank
    document_id: NonBlank
    document_version: NonBlank
    checksum: Checksum
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    section: NonBlank | None = None
    quote: NonBlank
    relation: Literal["supports", "contradicts"]

    @model_validator(mode="after")
    def require_locator(self) -> Self:
        if self.page is None and self.section is None:
            raise ValueError("assertion requires a source location")
        return self


class DiagnosticRule(Contract):
    code: NonBlank
    symptom: Symptom
    explanation: NonBlank
    missing_information: Annotated[tuple[NonBlank, ...], Field(min_length=1)]
    assertions: Annotated[tuple[SourceAssertion, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def require_support_and_unique_assertions(self) -> Self:
        if not any(item.relation == "supports" for item in self.assertions):
            raise ValueError("rule requires a supporting assertion")
        ids = [item.assertion_id for item in self.assertions]
        if len(ids) != len(set(ids)):
            raise ValueError("assertion IDs must be unique")
        return self


class DiagnosticCatalog(Contract):
    catalog_id: NonBlank
    catalog_version: NonBlank
    equipment_id: NonBlank
    scope: Literal["synthetic_demo"]
    rules: Annotated[tuple[DiagnosticRule, ...], Field(min_length=1, max_length=3)]

    @model_validator(mode="after")
    def require_unique_codes(self) -> Self:
        if len({item.code for item in self.rules}) != len(self.rules):
            raise ValueError("rule codes must be unique")
        return self


class Hypothesis(Contract):
    code: NonBlank
    explanation: NonBlank
    supporting_evidence_ids: Annotated[tuple[NonBlank, ...], Field(min_length=1)]
    contradicting_evidence_ids: tuple[NonBlank, ...] = ()
    uncertainty: Literal["unverified", "conflicting_evidence"]
    missing_information: Annotated[tuple[NonBlank, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def require_consistent_uncertainty(self) -> Self:
        if bool(self.contradicting_evidence_ids) != (self.uncertainty == "conflicting_evidence"):
            raise ValueError("uncertainty must reflect contradictory evidence")
        # One chunk may contain both supporting and contradicting statements.
        for ids in (self.supporting_evidence_ids, self.contradicting_evidence_ids):
            if len(set(ids)) != len(ids):
                raise ValueError("evidence IDs within a relation must be unique")
        return self


class AssertionMatch(Contract):
    rule_code: NonBlank
    assertion_id: NonBlank
    evidence_id: NonBlank
    document_id: NonBlank
    document_version: NonBlank
    checksum: Checksum
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    section: NonBlank | None = None
    relation: Literal["supports", "contradicts"]
    quote: NonBlank


class DiagnosticReport(Contract):
    request_id: NonBlank
    catalog_id: NonBlank
    catalog_version: NonBlank
    source_kind: Literal["synthetic"] = "synthetic"
    guidance_allowed: Literal[False] = False
    status: Literal["hypotheses_available", "needs_information", "blocked"]
    hypotheses: Annotated[tuple[Hypothesis, ...], Field(max_length=3)] = ()
    assertion_matches: tuple[AssertionMatch, ...] = ()
    missing_information: tuple[NonBlank, ...] = ()
    reason_code: NonBlank

    @model_validator(mode="after")
    def enforce_report_shape(self) -> Self:
        if (self.status == "hypotheses_available") != bool(self.hypotheses):
            raise ValueError("only available reports can contain hypotheses")
        if self.status == "needs_information" and not self.missing_information:
            raise ValueError("needs_information report requires missing information")
        codes = [item.code for item in self.hypotheses]
        if len(codes) != len(set(codes)):
            raise ValueError("hypothesis codes must be unique")
        if any(item.rule_code not in codes for item in self.assertion_matches):
            raise ValueError("assertion match references an unknown hypothesis")
        for hypothesis in self.hypotheses:
            for relation, ids in [
                ("supports", hypothesis.supporting_evidence_ids),
                ("contradicts", hypothesis.contradicting_evidence_ids),
            ]:
                matched_ids = {
                    item.evidence_id
                    for item in self.assertion_matches
                    if item.rule_code == hypothesis.code and item.relation == relation
                }
                if matched_ids != set(ids):
                    raise ValueError("hypothesis references must match citation relations")
        if any(item.page is None and item.section is None for item in self.assertion_matches):
            raise ValueError("citation location is required")
        if self.status != "hypotheses_available" and self.assertion_matches:
            raise ValueError("rejected reports must not contain assertion matches")
        return self
