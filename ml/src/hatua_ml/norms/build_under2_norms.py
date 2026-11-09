"""Under-24-month norms: status note (#32).

Implemented: gross motor, from the WHO Motor Development Study windows, as a
rule-based check (hatua_ml.norms.who_motor).

Not implemented: the other domains from Birth to Twenty (childdevdata gcdg_zaf).
Those items are assessor-administered, not caregiver-reported, and the cohort is
South African, so they do not match this system's feature space. Using them would
contradict the data-source rule recorded during the methodology review. Under-24
language, cognitive and social-emotional checks are left as future work.
"""
