# Chapter 5 test cases

Each case below is checked by the automated test named in the last column, so it can be
re-run at any time with `python -m pytest -q` from `backend/` (and `ml/` for TC019).

Run recorded here: 18 October 2026, development environment, synthetic model release
(`hatua_ml.synthetic`), 61 backend tests and the ML suite passing. TC019 needs the trained artefacts, so it was not run in that environment. Before using these
tables in the report, re-run them on your machine against the real release (1.1.0) and
update the date.

## Authentication and roles

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC001 | Caregiver self-registration | Name, Kenyan phone, password | Caregiver account created, signed in; any role in the request ignored | As expected | Pass | test_auth::test_register_makes_a_caregiver_and_signs_in |
| TC002 | Sign-in with wrong password or unknown number | Valid phone with wrong password; unregistered phone | Both refused with the same message | As expected | Pass | test_auth::test_wrong_password_and_unknown_number_get_the_same_answer |
| TC003 | Invalid or expired session | No token, malformed token, expired token, token signed with another key | Request refused (401) | As expected | Pass | test_auth::test_routes_need_a_valid_token |
| TC004 | Deactivated account | Administrator deactivates a caregiver | Caregiver can no longer sign in or use an existing session | As expected | Pass | test_auth::test_deactivated_account_cannot_sign_in_or_use_a_token |
| TC005 | Role restrictions | Caregiver calls CHW and admin routes; CHW calls admin routes | Refused (403) | As expected | Pass | test_access::test_role_gates |

## Child profiles and privacy

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC006 | Caregiver sees only their own children | Two caregivers, one child each | Each lists only their own child; the other child's records are not found | As expected | Pass | test_access::test_caregiver_sees_only_their_own_children |
| TC007 | CHW sees only linked caregivers' children | Two CHWs, one linked caregiver | Linked CHW sees the child; the other CHW sees none | As expected | Pass | test_access::test_chw_sees_children_of_linked_caregivers_only |
| TC008 | Age limits on a child profile | Date of birth over five years ago | Refused with a message | As expected | Pass | test_api_flow::test_ages_outside_coverage_are_refused |

## Assessment and prediction

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC009 | Model assessment, all milestones achieved | Child aged 48 months, 13 answers achieved | Low risk, no reasons, not sent to CHW, four domains shown | As expected | Pass | test_api_flow::test_whole_flow |
| TC010 | Model assessment, milestones not achieved | Child aged 48 months, 13 answers not achieved | Medium or high risk, top reasons as plain questions, sent to CHW | As expected | Pass | test_api_flow::test_whole_flow |
| TC011 | Under-24 milestone check | Child aged 20 months; then walking and standing alone not achieved | Six movement questions; low when achieved; high with two overdue milestones and months past the window | As expected | Pass | test_api_flow::test_under_24_months_uses_the_motor_milestone_check |
| TC012 | Invalid answers | An answer outside the options; a missing question; an extra question | Refused, naming the missing or unexpected questions | As expected | Pass | test_api_flow::test_bad_answers_are_refused |
| TC013 | Too young to assess | Child aged 2 months | Refused with a message to check from 4 months | As expected | Pass | test_api_flow::test_ages_outside_coverage_are_refused |

## CHW review and administration

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC014 | CHW records an outcome | Flagged result; outcome "refer to facility" | Case leaves the open list; caregiver sees the fixed referral message | As expected | Pass | test_api_flow::test_whole_flow |
| TC015 | "Unreachable" outcome | Flagged result; outcome "unreachable" | Outcome stored; no message shown to the caregiver | As expected | Pass | test_api_flow::test_unreachable_shows_the_caregiver_nothing |
| TC016 | Another CHW's case | CHW records an outcome on a case of a caregiver not linked to them | Refused (not found) | As expected | Pass | test_access::test_cases_and_outcomes_belong_to_the_linked_chw |
| TC017 | Usage summary | Two assessments (one low, one flagged), one outcome | Counts rise by exactly these amounts; a future date range shows none | As expected | Pass | test_admin::test_usage_summary_counts |
| TC018 | Deactivating a CHW with caregivers | CHW still linked to a caregiver | Refused until the caregiver is moved | As expected | Pass | test_admin::test_deactivation_rules |

## Model release integrity

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC019 | Altered release file | Release with a changed peer_stats.json | Release refused (checksum) | Not run here | Pending | ml test_export::test_altered_or_missing_file_is_refused (needs trained artefacts) |
| TC020 | Synthetic release in production | DEV_MODE=false with a synthetic release | API refuses to serve it | As expected | Pass | test_inference::test_synthetic_release_is_refused_outside_development |
