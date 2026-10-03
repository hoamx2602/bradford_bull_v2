from app.pipeline.teamid.classifier import VoteTracker, TARGET, OTHER, UNKNOWN
from app.pipeline.teamdet_video import _style, _C_PENDING
from app.pipeline.teamid.tracker import TrackedPerson
from app.pipeline.colors import brand_rgb, BRAND_HEX

def test_high_mass_conflict_does_not_imply_consensus():
    v=VoteTracker([TARGET,OTHER],decay=1)
    v.update(1,TARGET,10);v.label(1);v.update(1,OTHER,9)
    assert v.mass(1)==19 and v.margin(1,v.label(1))<.2

def test_hysteresis_stale_label_has_negative_margin():
    v=VoteTracker([TARGET,OTHER],decay=1)
    v.update(1,TARGET,10);v.label(1);v.update(1,OTHER,11)
    assert v.label(1)==TARGET and v.margin(1,TARGET)<0
    v.update(1,OTHER,5)
    assert v.label(1)==OTHER and v.margin(1,OTHER)>.2

def test_unknown_high_mass_drawn_pending():
    p=TrackedPerson((0,0,100,200),1,UNKNOWN,19)
    assert _style(p,2)==(_C_PENDING,'?')

def test_brand_colours_distinct_and_kit_independent():
    assert len(set(brand_rgb(k) for k in BRAND_HEX))==len(BRAND_HEX)
    assert brand_rgb('klg_home')==brand_rgb('klg_away')
    assert brand_rgb('acs_group')==brand_rgb('asc_group')
