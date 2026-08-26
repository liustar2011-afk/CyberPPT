# Stage 01 interaction and priority contract design

## Scope

Strengthen two existing lightweight Stage 01 contracts without creating an
interaction receipt or changing any Source Truth or Outline schema.

## Communication-goal interaction

`prepare_communication_strategy()` remains an in-memory preparation command.
Its returned instructions must make the live stop explicit: present two or
three source-supported routes, mark one recommendation, then stop and wait for
the user's selection, modification, or supplement.  The contract must also
continue to prohibit confirmation files, status JSON, approvals, receipts,
attempts, manifests, and ledgers.

A focused regression test will assert both the mandatory stop and the
no-artifact boundary, in addition to the existing no-files-written check.

## Source Truth priority hierarchy

Keep the current strict-mode policy unchanged: inventories under 40 records
are exempt; 40--79 records require at least one P2 retained-detail record; 80+
records require `max(5, ceil(records * 10%))` P2 records.  Document why the
policy is segmented and add boundary tests for 39, 40, 79, and 80 records.

## Verification

Run the focused communication-strategy and Source Truth contract tests.  The
tests must prove that the interaction remains artifact-free and that the
priority policy changes exactly at the documented boundaries.
