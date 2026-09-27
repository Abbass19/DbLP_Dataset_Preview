import gzip
from pathlib import Path

import pytest

from profile_dblp import profile, suggest_data_scope

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_gz(tmp_path) -> Path:
    xml_bytes = (FIXTURES / "sample.xml").read_bytes()
    gz_path = tmp_path / "sample.xml.gz"
    with gzip.open(gz_path, "wb") as fh:
        fh.write(xml_bytes)
    return gz_path


@pytest.fixture()
def sample_dtd() -> Path:
    return FIXTURES / "sample.dtd"


def test_record_counts_per_type(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    assert stats.type_counts["article"] == 2
    assert stats.type_counts["inproceedings"] == 2
    assert stats.type_counts["proceedings"] == 1
    assert stats.type_counts["www"] == 2


def test_entity_resolution(sample_gz, sample_dtd):
    # &uuml; must resolve to u-umlaut, not crash the parse or leave the raw entity.
    stats = profile(sample_gz, sample_dtd)
    assert stats.publication_total == 4  # article*2 + inproceedings*2 (proceedings excluded)


def test_field_completeness(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    # 4 authored records (proceedings excluded): 2 have ee, all 4 have author+year, 1 has crossref
    assert stats.field_present["ee"] == 2
    assert stats.field_present["author"] == 4
    assert stats.field_present["year"] == 4
    assert stats.field_present["crossref"] == 1


def test_authors_per_paper_distribution(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    # journals/tkde/Smith21: 2 authors, conf/kdd/Smith21: 2 authors,
    # conf/kdd/Wang22: 1 author, journals/tkde/Old99: 1 author
    assert stats.authors_per_paper[2] == 2
    assert stats.authors_per_paper[1] == 2


def test_papers_per_author_uses_orcid_when_available(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    # Jane Smith (orcid on every occurrence) authored 2 publication records
    assert stats.papers_per_author["orcid:0000-0001-1000-1000"] == 2
    # Wei Wang 0001 has no orcid attribute in this fixture, keyed by name text
    assert stats.papers_per_author["name:Wei Wang 0001"] == 2
    # "Someone NoOrcid" likewise has no orcid, keyed by name instead
    assert stats.papers_per_author["name:Someone NoOrcid"] == 1


def test_venue_prefix_extraction(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    # General DATA-2/DATA-4 overview: counts every non-www record with a key,
    # including the one "conf/kdd" proceedings container record itself.
    assert stats.venue_prefix_counts["journals/tkde"] == 2
    assert stats.venue_prefix_counts["conf/kdd"] == 3


def test_homonym_suffix_detection(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    assert stats.homonym_suffix_names["Wei Wang"] == 2  # appears twice as an author tag


def test_author_orcid_coverage(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    # Only Jane Smith's 3 occurrences (2 publications + 1 www) carry orcid.
    assert stats.author_tag_with_orcid == 3
    assert stats.author_tag_total > stats.author_tag_with_orcid


def test_www_alias_counts(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    assert stats.www_total == 2
    assert stats.www_alias_counts[1] == 1  # homepages/1/1000 has 1 author tag
    assert stats.www_alias_counts[2] == 1  # homepages/2/2000 has 2 (aliases)


def test_suggest_data_scope_shape(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd)
    scope = suggest_data_scope(stats, target_min=1, target_max=10)
    assert "start_year" in scope
    assert "venues" in scope
    assert scope["total_papers"] >= 1


def test_limit_caps_records(sample_gz, sample_dtd):
    stats = profile(sample_gz, sample_dtd, limit=1)
    assert sum(stats.type_counts.values()) == 1
