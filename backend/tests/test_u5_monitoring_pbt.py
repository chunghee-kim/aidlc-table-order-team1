"""U5 PBT — order status transitions (BR-U5-1/2) + delete-total recompute (BR-U5-5).

Targets the pure service core (`is_allowed_transition`, `ALLOWED`, `remaining_total`) so the
invariants run without a DB (business-logic-model §7).
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.order.admin import ALLOWED, VALID_STATUSES, is_allowed_transition, remaining_total

_status = st.sampled_from(VALID_STATUSES)


def _apply(cur: str, nxt: str) -> str:
    """State-machine step: move only on an allowed transition, otherwise stay put."""
    return nxt if is_allowed_transition(cur, nxt) else cur


# --- PBT-U5-STATE (BR-U5-1/2) --------------------------------------------------------------

@given(cur=_status, nxt=_status)
def test_transition_matches_table(cur, nxt):
    allowed = is_allowed_transition(cur, nxt)
    # (a) allowed ⇔ membership in ALLOWED[cur]; (b) never allow a no-op X->X.
    assert allowed == (nxt in ALLOWED[cur])
    if cur == nxt:
        assert not allowed


@settings(max_examples=200, deadline=None)
@given(seq=st.lists(_status, max_size=12))
def test_forward_only_and_terminal(seq):
    state = "대기중"
    reached_done = False
    for nxt in seq:
        prev = state
        state = _apply(state, nxt)
        # (c) once 완료 is reached, no transition ever changes the state again (terminal).
        if reached_done:
            assert state == "완료"
        # Monotonic order: 대기중(0) -> 준비중(1) -> 완료(2), never decreasing.
        order = {"대기중": 0, "준비중": 1, "완료": 2}
        assert order[state] >= order[prev]
        if state == "완료":
            reached_done = True


# --- PBT-U5-DELETE (BR-U5-5) ---------------------------------------------------------------

@given(
    totals=st.lists(st.integers(min_value=1, max_value=100_000), min_size=1, max_size=20),
    seed=st.integers(min_value=0),
)
def test_remaining_total_after_delete(totals, seed):
    i = seed % len(totals)
    new_total = remaining_total(totals, i)
    assert new_total == sum(totals) - totals[i]
    assert new_total == sum(totals[:i] + totals[i + 1:])
    if len(totals) == 1:
        assert new_total == 0
