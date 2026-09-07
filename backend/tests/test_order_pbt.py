"""U4/C property-based tests (Hypothesis) — order total & quantity invariants.

🔬 US-C-08/12: order total = Σ(unit_price × quantity); quantity >= 1;
order total == cart total (same formula on both sides). Also covers order-number sequencing.
"""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.errors import AppError, ErrorCode
from app.schemas.order import OrderItemInput
from app.services.order.create import (
    MAX_QUANTITY,
    PricedItem,
    _validate_items,
    line_total,
    next_order_number,
    order_total,
)

_prices = st.integers(min_value=1, max_value=1_000_000)
_qtys = st.integers(min_value=1, max_value=1000)
_valid_qtys = st.integers(min_value=1, max_value=MAX_QUANTITY)  # NFR-4: 항목당 1~99


@given(unit_price=_prices, quantity=_qtys)
def test_line_total_is_product(unit_price: int, quantity: int) -> None:
    assert line_total(unit_price, quantity) == unit_price * quantity


@given(
    lines=st.lists(st.tuples(_prices, _qtys), min_size=1, max_size=50),
)
def test_order_total_equals_sum_of_lines(lines: list[tuple[int, int]]) -> None:
    priced = [PricedItem(i, f"m{i}", up, q) for i, (up, q) in enumerate(lines)]
    # Order total == cart total: both are Σ(unit_price × quantity) over the same lines.
    cart_total = sum(up * q for up, q in lines)
    assert order_total(priced) == cart_total


@given(lines=st.lists(st.tuples(_prices, _qtys), min_size=0, max_size=20))
def test_order_total_never_negative(lines: list[tuple[int, int]]) -> None:
    priced = [PricedItem(i, f"m{i}", up, q) for i, (up, q) in enumerate(lines)]
    assert order_total(priced) >= 0


def test_empty_cart_is_rejected() -> None:
    with pytest.raises(AppError) as exc:
        _validate_items([])
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@given(quantity=st.integers(max_value=0))
def test_non_positive_quantity_rejected(quantity: int) -> None:
    with pytest.raises(AppError) as exc:
        _validate_items([OrderItemInput(menu_id=1, quantity=quantity)])
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@given(quantity=st.integers(min_value=MAX_QUANTITY + 1, max_value=10_000))
def test_over_cap_quantity_rejected(quantity: int) -> None:
    # NFR-4: 항목당 수량 상한 99. 초과 시 VALIDATION_ERROR.
    with pytest.raises(AppError) as exc:
        _validate_items([OrderItemInput(menu_id=1, quantity=quantity)])
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@given(quantity=_valid_qtys)
def test_in_range_quantity_accepted(quantity: int) -> None:
    _validate_items([OrderItemInput(menu_id=1, quantity=quantity)])  # no raise


@given(seq=st.integers(min_value=1, max_value=998))
def test_next_order_number_increments(seq: int) -> None:
    prefix = "20260831"
    nxt = next_order_number(prefix, f"{prefix}-{seq:03d}")
    assert nxt == f"{prefix}-{seq + 1:03d}"


def test_next_order_number_starts_at_001() -> None:
    assert next_order_number("20260831", None) == "20260831-001"
