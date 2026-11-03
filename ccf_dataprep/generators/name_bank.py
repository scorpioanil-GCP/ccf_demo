"""A synthetic person-name bank carrying real transliteration structure.

## Why a bank rather than a name generator

`kyc-refresh-beneficial-ownership` §F asks for person records with name
variants **across sources**, including **>= 2 transliteration cases**. The
estate's existing 571 variants are all `source='def14a'`,
`rendering='display_order'` — one source, one rendering, zero transliterations
(`docs/wave13b-design.md` §1.2). Counting them against a floor of 8 satisfies
the count and misses the condition entirely.

A transliteration case is not a misspelling. It arises because a name written
in one script admits several legitimate romanizations, and different registries
pick different ones:

    Дмитрий   -> Dmitry · Dmitri · Dmitriy · Dimitri
    يوسف      -> Yusuf · Youssef · Yousef · Jusuf
    Γεώργιος  -> Georgios · Yiorgos · George

Two random misspellings of an English name would satisfy a count of "variants"
while teaching nothing about the mechanism. So each entry here carries a native
form and the renderings that form genuinely admits, and the resolution layer
draws variants from that set.

Everything in this module is invented. No name here comes from the PSC
snapshot or any other register of real people — the snapshot supplies the
*shape distribution* the sampler matches against, never a name.

## Particles and their rendering instability

`van der`, `de la`, `al-`, `O'`, `Mc` are kept as a separate component because
registries disagree about capitalization, spacing and whether the particle
sorts with the surname. That disagreement is a second, independent source of
genuine variants, and it is orthogonal to script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random


@dataclass(frozen=True)
class NamePart:
    """One name component: a native form and the romanizations it admits."""

    native: str
    renderings: tuple[str, ...]
    #: True when the native form is not Latin script, so any Latin rendering is
    #: a transliteration rather than a spelling choice.
    transliterated: bool = False

    @property
    def preferred(self) -> str:
        return self.renderings[0]


def _p(native: str, *renderings: str, translit: bool = False) -> NamePart:
    return NamePart(native=native, renderings=tuple(renderings), transliterated=translit)


#: Script families. `latin_*` families romanize trivially (the native form IS a
#: rendering); the rest carry genuine transliteration ambiguity.
FORENAMES: dict[str, list[NamePart]] = {
    "latin_gb": [
        _p("Margaret", "Margaret", "Maggie", "Peggy"),
        _p("Katherine", "Katherine", "Catherine", "Kathryn"),
        _p("Geoffrey", "Geoffrey", "Jeffrey"),
        _p("Alistair", "Alistair", "Alasdair", "Alastair"),
        _p("Siobhan", "Siobhan", "Shivaun"),
        _p("Eleanor", "Eleanor", "Elinor"),
        _p("Nicholas", "Nicholas", "Nicolas"),
        _p("Rhiannon", "Rhiannon", "Rhianon"),
    ],
    "latin_continental": [
        _p("Henrik", "Henrik", "Henrick"),
        _p("Mathilde", "Mathilde", "Matilde"),
        _p("Joaquim", "Joaquim", "Joaquin"),
        _p("Anneliese", "Anneliese", "Annelise"),
        _p("Krzysztof", "Krzysztof", "Krystof"),
        _p("Ingeborg", "Ingeborg", "Ingebord"),
    ],
    "cyrillic": [
        _p("Дмитрий", "Dmitry", "Dmitri", "Dmitriy", "Dimitri", translit=True),
        _p("Екатерина", "Yekaterina", "Ekaterina", "Katerina", translit=True),
        _p("Сергей", "Sergey", "Sergei", "Serguei", translit=True),
        _p("Наталья", "Natalya", "Natalia", "Nataliya", translit=True),
        _p("Олександр", "Oleksandr", "Olexandr", "Alexander", translit=True),
    ],
    "arabic": [
        _p("يوسف", "Yusuf", "Youssef", "Yousef", "Jusuf", translit=True),
        _p("محمد", "Muhammad", "Mohammed", "Mohamad", "Mehmet", translit=True),
        _p("فاطمة", "Fatima", "Fatimah", "Fatma", translit=True),
        _p("خالد", "Khalid", "Khaled", "Chaled", translit=True),
        _p("زينب", "Zaynab", "Zeinab", "Zainab", translit=True),
    ],
    "greek": [
        _p("Γεώργιος", "Georgios", "Yiorgos", "George", translit=True),
        _p("Δημήτριος", "Dimitrios", "Demetrios", "Dimitris", translit=True),
        _p("Ελένη", "Eleni", "Heleni", "Helen", translit=True),
    ],
    "han": [
        _p("伟", "Wei", "Wai", translit=True),
        _p("俊杰", "Junjie", "Chun-chieh", "Jun Jie", translit=True),
        _p("秀英", "Xiuying", "Hsiu-ying", translit=True),
        _p("志强", "Zhiqiang", "Chih-chiang", translit=True),
    ],
    "devanagari": [
        _p("राजेश", "Rajesh", "Rajes", translit=True),
        _p("प्रिया", "Priya", "Priyaa", translit=True),
        _p("सुरेश", "Suresh", "Sureshe", translit=True),
    ],
}

SURNAMES: dict[str, list[NamePart]] = {
    "latin_gb": [
        _p("Ashworth", "Ashworth"), _p("Pennington", "Pennington"),
        _p("Fairbairn", "Fairbairn"), _p("Hollingsworth", "Hollingsworth"),
        _p("Thorne", "Thorne"), _p("Wycliffe", "Wycliffe"),
        _p("Barrowman", "Barrowman"), _p("Ledbetter", "Ledbetter"),
    ],
    "latin_continental": [
        _p("Vandersteen", "Vandersteen"), _p("Lindqvist", "Lindqvist", "Lindquist"),
        _p("Bergkamp", "Bergkamp"), _p("Wojciechowski", "Wojciechowski"),
        _p("Steenkamp", "Steenkamp"), _p("Brandeis", "Brandeis"),
    ],
    "cyrillic": [
        _p("Ковалёв", "Kovalyov", "Kovalev", "Kovaliov", translit=True),
        _p("Мельник", "Melnyk", "Melnik", translit=True),
        _p("Соловьёв", "Solovyov", "Soloviev", "Solovyev", translit=True),
        _p("Захарова", "Zakharova", "Zaharova", translit=True),
    ],
    "arabic": [
        # No built-in `Al-` here: the particle mechanism supplies it, and
        # carrying it in both places produced `al-Al-Husseini`.
        _p("حسيني", "Husseini", "Husayni", "Hussaini", translit=True),
        _p("نجار", "Najjar", "Naggar", "Nadjar", translit=True),
        _p("قاسم", "Qasim", "Kassem", "Kacem", translit=True),
    ],
    "greek": [
        _p("Παπαδόπουλος", "Papadopoulos", "Papadopulos", translit=True),
        _p("Βασιλείου", "Vasileiou", "Vassiliou", "Basileiou", translit=True),
    ],
    "han": [
        _p("张", "Zhang", "Chang", "Cheung", translit=True),
        _p("李", "Li", "Lee", "Lei", translit=True),
        _p("黄", "Huang", "Hwang", "Wong", translit=True),
    ],
    "devanagari": [
        _p("शर्मा", "Sharma", "Sarma", translit=True),
        _p("मुखर्जी", "Mukherjee", "Mukerji", "Mukhopadhyay", translit=True),
    ],
}

#: Nobiliary and patronymic particles, with the renderings registries disagree
#: over. Independent of script: a `van der` name is Latin throughout and still
#: produces genuine cross-registry variants.
PARTICLES: dict[str, tuple[str, ...]] = {
    "van der": ("van der", "Van Der", "vander"),
    "de la": ("de la", "De La", "dela"),
    "von": ("von", "Von"),
    "al-": ("al-", "Al-", "al "),
    "O'": ("O'", "O", "O’"),
    "Mc": ("Mc", "Mac"),
    "St": ("St", "St.", "Saint"),
}

#: Which particles each naming tradition actually uses.
ELIGIBLE_PARTICLES: dict[str, tuple[str, ...]] = {
    "latin_gb": ("O'", "Mc", "St"),
    "latin_continental": ("van der", "von", "de la"),
    "arabic": ("al-",),
}

#: Particles written flush against the surname. The rest take a space.
NO_SPACE_PARTICLES = frozenset({"O'", "Mc", "al-"})

TITLES: tuple[str, ...] = ("Mr", "Mrs", "Ms", "Miss", "Dr", "Professor")


@dataclass
class SyntheticName:
    """One invented identity, with everything needed to render it many ways."""

    script_family: str
    given: NamePart
    family: NamePart
    middle: NamePart | None = None
    particle: str | None = None
    title: str | None = None
    hyphenated_family: NamePart | None = None
    _rng: Random = field(default_factory=Random, repr=False)

    @property
    def transliterated(self) -> bool:
        return self.given.transliterated or self.family.transliterated

    def surname(self, rendering_index: int = 0) -> str:
        base = self.family.renderings[rendering_index % len(self.family.renderings)]
        if self.hyphenated_family is not None:
            second = self.hyphenated_family.renderings[
                rendering_index % len(self.hyphenated_family.renderings)
            ]
            base = f"{base}-{second}"
        if self.particle:
            forms = PARTICLES[self.particle]
            prefix = forms[rendering_index % len(forms)]
            # Some particles bind directly to the surname (O'Brien, McLeod,
            # al-Najjar), others stand off it (van der Steen). Registries
            # disagree about the stand-off ones far more often, which is why
            # the two groups are named rather than guessed from punctuation.
            joiner = "" if self.particle in NO_SPACE_PARTICLES else " "
            base = f"{prefix}{joiner}{base}"
        return base

    def forename(self, rendering_index: int = 0) -> str:
        return self.given.renderings[rendering_index % len(self.given.renderings)]

    def display(self, rendering_index: int = 0) -> str:
        """`First Middle Last` — the form most registries publish."""
        parts = [self.forename(rendering_index)]
        if self.middle:
            parts.append(self.middle.renderings[
                rendering_index % len(self.middle.renderings)])
        parts.append(self.surname(rendering_index))
        return " ".join(parts)

    def rendering_count(self) -> int:
        """How many genuinely distinct renderings this identity admits."""
        n = max(len(self.given.renderings), len(self.family.renderings))
        if self.particle:
            n = max(n, len(PARTICLES[self.particle]))
        return n


def sample_name(
    rng: Random,
    *,
    script_family: str,
    has_middle: bool,
    has_particle: bool,
    hyphenated: bool,
    has_title: bool,
) -> SyntheticName:
    """Invent one identity matching a requested SHAPE.

    The shape comes from the PSC distribution; the name comes from here. The
    two never meet — no character of a real name reaches this function.
    """
    fam = script_family if script_family in FORENAMES else "latin_gb"
    given = rng.choice(FORENAMES[fam])
    family = rng.choice(SURNAMES[fam])
    middle = None
    if has_middle:
        # Resampled until distinct: `Eleni Eleni Papadopoulos` is not a name
        # shape any register produces, and it would inflate the token-overlap
        # score the resolver uses.
        pool = [f for f in FORENAMES[fam] if f.native != given.native]
        middle = rng.choice(pool) if pool else None
    second_family = rng.choice(SURNAMES[fam]) if hyphenated else None

    # Particles belong to naming traditions, not to names in general. A
    # Cyrillic surname does not take `de la`, and an earlier fallback that
    # handed one to every family produced `de la Solovyov`. A family with no
    # eligible particle simply gets none, even when the shape asked for one —
    # the shape distribution is a target, not a licence to invent a tradition.
    eligible = ELIGIBLE_PARTICLES.get(fam, ())
    particle = rng.choice(eligible) if (has_particle and eligible) else None

    return SyntheticName(
        script_family=fam,
        given=given,
        family=family,
        middle=middle,
        particle=particle,
        title=rng.choice(TITLES) if has_title else None,
        hyphenated_family=second_family,
        _rng=rng,
    )
