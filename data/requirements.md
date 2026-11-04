# Sample game requirements

These rules describe only the vendored toy game, not a commercial game.
Review them against the upstream implementation before authoring test oracles.

- R1: A locked door requires a key. Entering it opens the door and consumes one key; with no key it stays closed and blocks entry.
- R2: Using a potion at full HP does not consume it.
- R3: Using a potion at reduced HP heals without exceeding max_hp and consumes one potion when available.
- R4: Buying a potion with fewer than five gold does not change gold or inventory.
- R5: Buying a potion with at least five gold consumes five gold and adds one potion.
- R6: Walls and void tiles block movement; a move must not pass through them.
- R7: Collecting a reachable key adds inventory without crashing, including when the player already holds two keys.
- R8: Enemy attacks reduce HP; dead must agree with HP <= 0. Other events in the same turn must be considered.
- R9: Entering the goal ends the game with won=true.

Day-2 target: 18 manually reviewed cases covering these nine requirements,
with normal, boundary or negative checks chosen to fit each mechanic.
The included starter has only three example cases for R1, R2 and R4.
