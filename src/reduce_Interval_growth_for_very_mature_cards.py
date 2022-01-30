# License AGPLv3

import sys
import math

from anki.cards import Card
from anki.scheduler.v1 import Scheduler as oldsched
from anki.scheduler.v2 import Scheduler as v2sched

from aqt import mw
from aqt.utils import showInfo
from anki.hooks import wrap

from .config import gc


def _modify_ivl_for_very_mature_cards(self, prelim_new_ivl, conf, fct, mult):
    """all inputs are integers and fractions of integers are rounded down"""
    red = gc("don't reduce ivls if they are already capped by the deck maxIvl")

    min_mod_fct = math.sqrt(fct)

    # Modify factor to decrease depending on how large ivl is
    full_mod_ivl = mult * (prelim_new_ivl / fct) * min_mod_fct
    # Multiply days_upper by factor, this means that
    # Higher ease = longer change to logarithmic growth = lower review frequency
    # This keeps high ease cards different from low ease even when they're very mature
    adj_days_upper = float(gc("days_upper")) * fct

    if red and prelim_new_ivl > conf["maxIvl"]:
        return prelim_new_ivl
    if prelim_new_ivl - gc("days_lower") <= 0:
        return int(prelim_new_ivl)
    elif prelim_new_ivl - adj_days_upper > 0:
        return int(full_mod_ivl)
    else:
        days_range = float(adj_days_upper - gc("days_lower"))
        days_over_lower = prelim_new_ivl - gc("days_lower")
        p = days_over_lower / days_range
        # Return gradually increasing portion of fully modded vs normal ivl
        mod_ivl = int(min(prelim_new_ivl, prelim_new_ivl * (1 - p) + full_mod_ivl * p))
        print('mod_ivl', prelim_new_ivl, mod_ivl)
        return mod_ivl


# this is a modified version of _nextRevIvl from sched.py
def nextRevIvlMod__v1(self, card, ease):
    "Ideal next interval for CARD, given EASE."
    delay = self._daysLate(card)
    conf = self._revConf(card)
    fct = card.factor / 1000.0

    ###start of modification###
    if card.ivl >= gc("delay: don't modify delay for cards with ivls below"):
        delay = int(delay * gc("delay: percentage")/100.0)

    if gc("ease_min"):
        min_fct = gc("ease_min")/100.0
        if min_fct >= fct:
            fct = min_fct
    if gc("ease_max"):
        max_fct = gc("ease_max")/100.0
        if max_fct <= fct:
            fct = max_fct
    ###end of modification###

    prelim_ivl2 = self._constrainedIvl(
        (card.ivl + delay // 4) * 1.2, conf, card.ivl)
    prelim_ivl3 = self._constrainedIvl(
        (card.ivl + delay // 2) * fct, conf, prelim_ivl2)
    prelim_ivl4 = self._constrainedIvl(
        (card.ivl + delay) * fct * conf['ease4'], conf, prelim_ivl3)

    ###start of modification###
    ivl2 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl2, conf, fct, 1)
    ivl3 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl3, conf, fct, 1)
    ivl4 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl4, conf, fct, conf['ease4'])
    ###end of modification###

    if ease == 2:
        interval = ivl2
    elif ease == 3:
        interval = ivl3
    elif ease == 4:
        interval = ivl4
    # interval capped?
    return min(interval, conf['maxIvl'])


def nextRevIvlMod__v2(self, card: Card, ease: int, fuzz: bool) -> int:
    "Next review interval for CARD, given EASE."
    delay = self._daysLate(card)
    conf = self._revConf(card)
    fct = card.factor / 1000
    hardFactor = conf.get("hardFactor", 1.2)

    if hardFactor > 1:
        hardMin = card.ivl
    else:
        hardMin = 0

    ###start of modification###
    if card.ivl >= gc("delay: don't modify delay for cards with ivls below"):
        delay = int(delay * gc("delay: percentage")/100.0)

    if gc("ease_min"):
        min_fct = gc("ease_min")/100.0
        if min_fct >= fct:
            fct = min_fct
    if gc("ease_max"):
        max_fct = gc("ease_max")/100.0
        if max_fct <= fct:
            fct = max_fct


    f = self._constrainedIvl
    prelim_ivl2 = f(card.ivl * hardFactor,
                    conf, hardMin,     fuzz)
    prelim_ivl3 = f((card.ivl + delay // 2) * fct,
                    conf, prelim_ivl2, fuzz)
    prelim_ivl4 = f((card.ivl + delay) * fct *
                    conf["ease4"], conf, prelim_ivl3, fuzz)

    ivl2 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl2, conf, fct, 1)
    ivl3 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl3, conf, fct, 1)
    ivl4 = _modify_ivl_for_very_mature_cards(
        self, prelim_ivl4, conf, fct, conf['ease4'])
    ###end of modification###

    if ease == 2:
        return ivl2
    if ease == 3:
        return ivl3
    return ivl4


oldsched.original_nextRevIvl = oldsched._nextRevIvl  # for add-on sidebar for scheduler comparison
oldsched._nextRevIvl = nextRevIvlMod__v1
v2sched.original_nextRevIvl = v2sched._nextRevIvl
v2sched._nextRevIvl = nextRevIvlMod__v2
