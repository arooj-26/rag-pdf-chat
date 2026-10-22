from evaluation.run import run


def test_reproducible_rankings():
    first, second = run(3), run(3)
    assert first["document_count"] == 8
    assert first["answer_groundedness"] is None
    for mode in first["results"]:
        a, b = first["results"][mode], second["results"][mode]
        assert a["hit_rate_at_k"] == b["hit_rate_at_k"]
        assert [q["retrieved"] for q in a["questions"]] == [q["retrieved"] for q in b["questions"]]
