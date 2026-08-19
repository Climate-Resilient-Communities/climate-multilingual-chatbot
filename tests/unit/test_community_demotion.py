"""Tests for demotion of neighbourhood-scoped docs on city-general queries.

The knowledge base carries dense curated collections for specific communities
(e.g. Thorncliffe Park). Without demotion, those docs dominate retrieval for
ANY Toronto-level climate query and every general answer ends up spotlighting
one neighbourhood.
"""

from src.models.retrieval import _demote_unrequested_community_docs


def _doc(title, section="", score=0.9):
    return {"title": title, "section_title": section, "score": score, "content": "x"}


GENERAL_1 = _doc("TransformTO Net Zero Strategy", "City of Toronto", 0.82)
THORN_TITLED = _doc("Thorncliffe Park Flood Vulnerability — Don River Watershed",
                    "Thorncliffe Park Climate Resilience", 0.90)
THORN_SECTION_ONLY = _doc("Don River Watershed Overview",
                          "Thorncliffe Park Climate Resilience", 0.88)
GENERAL_2 = _doc("Toronto's Future Weather & Climate Drivers Study", "", 0.80)


class TestCityGeneralQueries:
    def test_community_docs_move_behind_general_docs(self):
        docs = [THORN_TITLED, THORN_SECTION_ONLY, GENERAL_1, GENERAL_2]
        out = _demote_unrequested_community_docs(
            "What are the local impacts of climate change in Toronto?", docs)
        titles = [d["title"] for d in out]
        assert titles == [GENERAL_1["title"], GENERAL_2["title"],
                          THORN_TITLED["title"], THORN_SECTION_ONLY["title"]]

    def test_section_title_alone_identifies_community_docs(self):
        out = _demote_unrequested_community_docs(
            "climate change in Toronto", [THORN_SECTION_ONLY, GENERAL_1])
        assert out[0]["title"] == GENERAL_1["title"]

    def test_demoted_docs_get_score_penalty(self):
        out = _demote_unrequested_community_docs(
            "climate change in Toronto", [THORN_TITLED, GENERAL_1], penalty=0.15)
        by_title = {d["title"]: d for d in out}
        assert by_title[THORN_TITLED["title"]]["score"] == 0.90 - 0.15
        assert by_title[GENERAL_1["title"]]["score"] == 0.82  # untouched

    def test_general_docs_keep_relative_order(self):
        out = _demote_unrequested_community_docs(
            "climate change in Toronto", [GENERAL_1, THORN_TITLED, GENERAL_2])
        assert [d["title"] for d in out[:2]] == [GENERAL_1["title"], GENERAL_2["title"]]


class TestCommunityQueriesKeepTheirDocs:
    def test_query_naming_the_community_is_not_demoted(self):
        docs = [THORN_TITLED, GENERAL_1]
        out = _demote_unrequested_community_docs(
            "What should I know about flooding in Thorncliffe Park?", docs)
        assert [d["title"] for d in out] == [THORN_TITLED["title"], GENERAL_1["title"]]
        assert out[0]["score"] == 0.90  # no penalty

    def test_case_insensitive_query_match(self):
        out = _demote_unrequested_community_docs(
            "flooding in THORNCLIFFE park", [THORN_TITLED, GENERAL_1])
        assert out[0]["title"] == THORN_TITLED["title"]


class TestEdgeCases:
    def test_empty_docs(self):
        assert _demote_unrequested_community_docs("anything", []) == []

    def test_zero_penalty_disables_demotion(self):
        docs = [THORN_TITLED, GENERAL_1]
        assert _demote_unrequested_community_docs("toronto", docs, penalty=0.0) == docs

    def test_custom_markers(self):
        rexdale = _doc("Rexdale Heat Vulnerability", "", 0.9)
        out = _demote_unrequested_community_docs(
            "heat in Toronto", [rexdale, GENERAL_1], markers=("rexdale",))
        assert out[0]["title"] == GENERAL_1["title"]
