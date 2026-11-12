"""Under-24-month norms: status note (#32).

Implemented: gross motor, from the WHO Motor Development Study windows, as a
rule-based check (hatua_ml.norms.who_motor). It now serves as the baseline for
the under-24 model.

Decision change (Nov 2026): the project scope moved beyond Kenya and the
0-24 month band became the focus. The earlier rule against assessor-administered
childdevdata was relaxed for this band, because no open caregiver-reported
under-24 dataset with milestone labels exists. The under-24 model is trained on
the Dutch SMOCC cohort (hatua_ml.features.build_under2_table), with the
assessor-versus-caregiver mismatch stated as a limitation. Other childdevdata
cohorts use different instruments and share no items with SMOCC; adding them
needs a manual milestone crosswalk (future work).
"""
