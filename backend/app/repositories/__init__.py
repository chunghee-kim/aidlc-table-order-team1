"""Repository interfaces (contract frozen in Phase 0). Signatures per component-methods.md §2.

Each repo file is owned by a single Phase 1 stream (see unit-of-work.md §3):
  store/admin_user/table/session -> U2/A ; menu/category -> U3/B ; order -> U4/C ; order_history -> U6/E.
Streams provide concrete implementations of these Protocols. Do not change signatures unilaterally.
"""
