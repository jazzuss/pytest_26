"""The levels, their monsters and their XP.

Instructors: this is the file to edit. Every monster's `find` text must appear
exactly once in its dungeon file. `python -m grader selftest` checks that, and
`python -m grader seal` must be run after any change here or in src/.
"""

from __future__ import annotations

from grader import checks
from grader.model import Level, Mutant

LEVELS: tuple[Level, ...] = (
    Level(
        0, "The Gate", "running pytest and reading a failure", 50,
        mutants=(
            Mutant("The Nameless One", "gate.py",
                   'return f"Welcome to the dungeon, {name}!"',
                   'return "Welcome to the dungeon, stranger!"',
                   "The gatekeeper forgot the hero's name. Does your test still check the greeting?"),
        ),
    ),
    Level(
        1, "First Blood", "test functions and plain assert", 100, min_tests=3,
        mutants=(
            Mutant("The Bottomless Pit", "hero.py",
                   "self.hp = max(self.hp - amount, 0)", "self.hp = self.hp - amount",
                   "Someone took a huge hit, and their hp went somewhere strange."),
            Mutant("The Overflowing Flask", "hero.py",
                   "self.hp = min(self.hp + amount, self.max_hp)", "self.hp = self.hp + amount",
                   "A healing potion worked a little TOO well."),
            Mutant("The Undying", "hero.py",
                   "return self.hp > 0", "return self.hp >= 0",
                   "A hero with 0 hp is still walking around."),
            Mutant("The Off-By-One Imp", "hero.py",
                   "while self.xp >= XP_PER_LEVEL:", "while self.xp > XP_PER_LEVEL:",
                   "Exactly 100 xp should be enough to level up. Is it? (Test the boundary.)"),
            Mutant("The One-Level Wonder", "hero.py",
                   "while self.xp >= XP_PER_LEVEL:", "if self.xp >= XP_PER_LEVEL:",
                   "Gaining a LOT of xp at once should give more than one level."),
        ),
    ),
    Level(
        2, "Keen Eye", "assertions: approx, collections and None", 100, min_tests=3,
        mutants=(
            Mutant("The Rounding Gremlin", "inventory.py",
                   "return sum(self._items[name].weight * count for name, count in self._counts.items())",
                   "return round(sum(self._items[name].weight * count for name, count in self._counts.items()))",
                   "Light things like a 0.1 kg potion stopped weighing anything. Compare floats with pytest.approx."),
            Mutant("The Featherweight", "inventory.py",
                   "self._items[name].weight * count", "self._items[name].weight",
                   "Three potions weigh three times as much as one. Or do they?"),
            Mutant("The Shuffler", "inventory.py",
                   "return sorted(self._counts)", "return list(self._counts)",
                   "names() promises alphabetical order. Add things in a non-alphabetical order and compare the whole list."),
            Mutant("The Impostor", "inventory.py",
                   "return self._items.get(name)", "return self._items.get(name, Item(name, 0.0))",
                   "Looking for something you don't carry should give None. Check it with `is None`."),
            Mutant("The Phantom Stack", "inventory.py",
                   "return {name: count for name, count in self._counts.items()}",
                   "return {name: 1 for name in self._counts}",
                   "as_dict() should say how MANY of each item you carry. Compare the whole dict."),
        ),
    ),
    Level(
        3, "When Things Go Wrong", "pytest.raises, match= and pytest.warns", 150, min_tests=4,
        mutants=(
            Mutant("The Ghost Blow", "hero.py",
                   '            raise ValueError("damage cannot be negative")',
                   "            amount = 0",
                   "Negative damage is nonsense and must raise ValueError, but now nothing happens."),
            Mutant("The Necromancer", "hero.py",
                   "if not self.is_alive:", "if False:",
                   "Dead heroes can't be healed. Some exceptions are custom ones (HeroIsDeadError)."),
            Mutant("The Silent Herald", "hero.py",
                   '        warnings.warn(\n'
                   '            "battle_cry() is deprecated, use shout() instead",\n'
                   '            DeprecationWarning,\n'
                   '            stacklevel=2,\n'
                   '        )\n',
                   "",
                   "battle_cry() is deprecated and must warn about it. Warnings can be tested too."),
            Mutant("The Shapeshifter", "inventory.py",
                   'raise InventoryFullError(f"{item.name} is too heavy to carry")',
                   'raise ValueError(f"{item.name} is too heavy to carry")',
                   "The backpack still complains when it's too heavy, but with the wrong TYPE of exception."),
            Mutant("The Mumbler", "dice.py",
                   'raise ValueError(f"invalid dice notation: {notation!r}")',
                   'raise ValueError(f"bad dice: {notation!r}")',
                   "The error message is part of the contract. pytest.raises(..., match=...) checks it."),
        ),
    ),
    Level(
        4, "Many Faces", "@pytest.mark.parametrize", 150, min_tests=6,
        checks=(checks.parametrized(6),),
        mutants=(
            Mutant("The Weak Crit", "combat.py",
                   "damage *= 2", "damage += 2",
                   "Critical hits feel weaker than they should."),
            Mutant("The Glass Jaw", "combat.py",
                   "return max(damage, 1)", "return max(damage, 0)",
                   "Every hit deals at least 1 damage, even against a huge defense."),
            Mutant("Elemental Chaos", "combat.py",
                   "if element is not None and element == weakness:", "if element is not None:",
                   "Fire against a target weak to ice shouldn't get a bonus."),
            Mutant("The Void Element", "combat.py",
                   "if element is not None and element == weakness:", "if element == weakness:",
                   "A plain hit (no element, no weakness) suddenly gets the weakness bonus."),
            Mutant("The Generous Rounder", "combat.py",
                   "damage = damage * 3 // 2", "damage = -(-damage * 3 // 2)",
                   "x1.5 must be rounded DOWN. Try a case where the damage is odd."),
            Mutant("The Shieldbreaker", "combat.py",
                   "if attack < 0 or defense < 0:", "if attack < 0:",
                   "A negative defense should be rejected too. Error cases belong in your table."),
        ),
    ),
    Level(
        5, "Gear Up", "fixtures and conftest.py", 200, min_tests=4,
        checks=(checks.conftest_fixtures(2),),
        mutants=(
            Mutant("Free Lunch", "shop.py",
                   "hero.gold -= listing.price", "hero.gold -= 0",
                   "Shopping has become suspiciously cheap."),
            Mutant("The Endless Shelf", "shop.py",
                   "listing.stock -= 1", "listing.stock -= 0",
                   "The shop never runs out, however much you buy."),
            Mutant("The Generous Merchant", "shop.py",
                   "payout = item.value // 2", "payout = item.value",
                   "Selling pays more than it should."),
            Mutant("The Loan Shark", "shop.py",
                   "if hero.gold < listing.price:", "if hero.gold < 0:",
                   "Heroes can buy things they can't afford."),
            Mutant("The Pickpocket", "shop.py",
                   "inventory.add(listing.item)\n        hero.gold -= listing.price",
                   "hero.gold -= listing.price\n        inventory.add(listing.item)",
                   "When the backpack is too full to take the item, the hero still pays."),
        ),
    ),
    Level(
        6, "Tools of the Trade", "tmp_path, capsys and monkeypatch", 200, min_tests=5,
        checks=(checks.uses_fixtures("tmp_path", "capsys", "monkeypatch"),),
        mutants=(
            Mutant("Amnesia", "savegame.py",
                   'gold=hero["gold"],', "gold=0,",
                   "After loading a save, something valuable is missing."),
            Mutant("The Gullible Loader", "savegame.py",
                   'if data.get("version") != SAVE_VERSION:', "if False:",
                   "Old or foreign save files should be rejected with CorruptSaveError."),
            Mutant("The Shallow Grave", "savegame.py",
                   "path.parent.mkdir(parents=True, exist_ok=True)", "pass",
                   "save() promises to create missing folders. Save into a folder that doesn't exist yet."),
            Mutant("The Off-Key Bard", "bard.py",
                   ", file=sys.stderr)", ")",
                   "The worried remark should go to stderr, not stdout."),
            Mutant("The Stubborn Clerk", "config.py",
                   ".strip().lower()", ".strip()",
                   "DUNGEON_DIFFICULTY=HARD should work just like hard."),
            Mutant("The Hardcore Default", "config.py",
                   'os.environ.get(ENV_VAR, "normal")', 'os.environ.get(ENV_VAR, "hard")',
                   "With no DUNGEON_DIFFICULTY set at all, the game should be normal."),
        ),
    ),
    Level(
        7, "Marked", "custom marks, skipif, strict xfail and -m", 200, min_tests=4,
        pytest_args=("--strict-markers",),
        checks=(
            checks.registered_marker("slow"),
            checks.marker_used("slow"),
            checks.fast_without("slow"),
            checks.skipif_with_reason,
            checks.strict_xfail,
        ),
        mutants=(
            Mutant("The Silent Fix", "dice.py",
                   "modifier = abs(int(match.group(3))) if match.group(3) else 0",
                   "modifier = int(match.group(3)) if match.group(3) else 0",
                   "Someone fixed bug #13 and nobody noticed. A STRICT xfail test would have told you."),
            Mutant("The False Prophet", "oracle.py",
                   'if not question.rstrip().endswith("?"):', "if not question:",
                   "The oracle only answers questions ending with '?'."),
            Mutant("The Wandering Oracle", "oracle.py",
                   "return PROPHECIES[index]", 'return "Ask again later."',
                   "Every answer must come from the oracle's PROPHECIES."),
            Mutant("The Closed Portal", "portal.py",
                   'return f"A shimmering portal to {destination} opens."', 'return "A portal opens."',
                   "On Linux and macOS the portal should name its destination.", posix_only=True),
        ),
    ),
    Level(
        8, "Smoke and Mirrors", "mocking: patch where it's used, side_effect, call checks", 250,
        min_tests=4,
        checks=(checks.uses_test_doubles,),
        mutants=(
            Mutant("Crossed Wires", "raven.py",
                   'json.dumps({"to": recipient, "message": message})',
                   'json.dumps({"to": message, "message": recipient})',
                   "The raven carries the right words to the wrong place. Check WHAT was sent."),
            Mutant("The Quitter", "raven.py",
                   "for _ in range(attempts):", "for _ in range(1):",
                   "One network hiccup and the raven gives up. Make the first calls fail (side_effect)."),
            Mutant("The Pest", "raven.py",
                   "for _ in range(attempts):", "for _ in range(attempts + 1):",
                   "The raven tries one time too many. Count the calls."),
            Mutant("Lost in Silence", "raven.py",
                   '    raise RavenLostError(f"the raven to {recipient} was lost after {attempts} attempts")',
                   '    return ""',
                   "When every attempt fails, you should hear about it (RavenLostError)."),
            Mutant("The Eternal Wait", "raven.py",
                   "urlopen(request, timeout=TIMEOUT_SECONDS)", "urlopen(request)",
                   "The raven must never wait forever: check the timeout it was called with."),
        ),
    ),
    Level(
        9, "No Stone Unturned", "coverage, and why it isn't enough", 250, min_tests=6,
        checks=(checks.coverage("quests.py", 100),),
        mutants=(
            Mutant("The Lenient Clock", "quests.py",
                   "if quest.deadline <= 0:", "if quest.deadline < 0:",
                   "A quest whose deadline reaches exactly 0 should fail."),
            Mutant("The Cheater's Reward", "quests.py",
                   "if quest.state is not QuestState.COMPLETED:", "if quest.state is QuestState.FAILED:",
                   "Rewards for a quest that was never completed?"),
            Mutant("The Sticky Progress", "quests.py",
                   "quest.done.clear()", "pass",
                   "Abandoning a quest should wipe its progress."),
            Mutant("The Overbooked Hero", "quests.py",
                   "if len(self.active()) >= self.max_active:", "if len(self.active()) > self.max_active:",
                   "max_active means at most that many, not one more."),
            Mutant("The Level Skipper", "quests.py",
                   "if hero.level < quest.required_level:", "if hero.level + 1 < quest.required_level:",
                   "A hero one level too low got into a quest. Test right at the boundary."),
        ),
    ),
)

BOSS_XP = 500
MAX_XP = sum(level.xp for level in LEVELS) + BOSS_XP

RANKS = (
    (0, "Peasant"),
    (50, "Squire"),
    (350, "Knight"),
    (800, "Champion"),
    (1400, "Paladin"),
    (1650, "Hero"),
    (MAX_XP, "Legend of Pytest"),
)


def rank(xp: int) -> tuple[str, tuple[int, str] | None]:
    """(current rank, (xp needed, next rank) or None)."""
    current = RANKS[0][1]
    for threshold, name in RANKS:
        if xp >= threshold:
            current = name
        else:
            return current, (threshold, name)
    return current, None


def by_number(number: int) -> Level:
    for level in LEVELS:
        if level.number == number:
            return level
    raise KeyError(number)
