# Persistence (flash)

What the node keeps across power loss, and how it stores it without wearing
out the nRF52832's internal flash. No external memory part — the internal
flash is plenty.

## What's persisted

- **Last accepted replay counter** — always required. If it resets to 0 on
  reboot, any previously sniffed command frame becomes valid again (see
  [protocol.md](protocol.md)).
- **Commanded output state (ON/OFF)** — required: the switching element is
  a MOSFET with no memory of its own (the Jeti SPS-20 approach; see
  [hardware.md](hardware.md)'s Switching stage). Firmware restores it on
  boot within ~20ms of power-up, before the hardware's slow turn-on lets
  the load switch start conducting.

Both are written **together, only when an accepted command changes the
state**. Repeats of the current state are never written: commands are
absolute state, so replaying a same-state frame is harmless, and any older
frame that *would* change state carries a counter below the last persisted
one. The counter therefore costs no extra flash writes.

## Flash constraints (nRF52832)

- Erase sets a whole 4 KB page to all 1s; a write can only clear bits
  (1→0). Endurance is **10,000 erase cycles per page** — writes into
  already-erased space don't count against it.
- The NVMC also limits how many times the same word / block may be written
  between erases (`n_WRITE`, `n_WRITE,BLOCK` in the Product Specification's
  NVMC chapter — verify exact values there). Writing each word exactly once
  stays within both, so no bit-by-bit tricks.
- Word write ≈ 40 µs. Page erase ≈ 85 ms and stalls the CPU — keep it out
  of the command path.

## Scheme: append-only log over two pages

Two dedicated, reserved flash pages, A and B, both erased at first boot.

- **Record** = 8 bytes (two words), appended to the next free slot:
  - word 0: replay counter (32-bit, so it also covers a future widened
    counter — see protocol.md open items)
  - word 1: `0xA5` marker | reserved | state byte | inverted state byte
- **Write order**: counter word first, marker word last. A record only
  counts as valid once its marker word is valid, so a power cut mid-write
  leaves at worst an ignored half-record.
- **Boot**: scan A and B for the last valid record → restore state and
  counter. No valid record (fresh device) → OFF, counter 0.
- **Rollover**: when the active page is full (512 records), continue in the
  other page — it's already erased, so no erase in the command path. Erase
  the full page afterwards, while idle (not during a scan window). The new
  page always has a valid record before the old one is erased, so a power
  cut during erase never loses state.
- **Write verify / wear-out fallback**: read back each record after
  writing. On mismatch, keep running with state + counter in RAM and set a
  "flash worn" flag reported in the ack. The switch never bricks — it only
  loses power-loss memory.

## Lifetime

Each page is erased once per 1024 records (512 in A + 512 in B), so:
10,000 × 1024 ≈ **10 million state changes** — ~270 years at 100 changes
a day. Erase happens once per 512 changes, never inline with a command.

## Implementation note

Zephyr/NCS NVS and nRF5 SDK FDS both provide append-only wear-levelled
storage with torn-write recovery and could replace the hand-rolled scheme.
The hand-rolled version is ~50 lines and fully deterministic; which to use
follows from the (still open) toolchain choice.
