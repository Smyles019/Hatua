# Chapter 5 test cases

Each case below is checked by the automated test named in the last column, so it can be
re-run at any time: `python -m pytest -q` from `backend/` and from `ml/`, and
`flutter test` from `app/`.

Run recorded here: 9 November 2026, development machine (Windows), Python 3.14.

- ML suite: 147 passed, none skipped, using the trained artefacts.
- Backend suite: 84 passed. The API flow tests run on the synthetic 24 to 59 month
  release (`hatua_ml.synthetic`), so they need no survey data, and on the real
  under-24 model (`ml/artefacts/xgboost_under2/short_30`).
- App suite: 15 passed.
- TC009 and TC010 were also run directly against the real release 1.1.0 (13 questions):
  all achieved gave low risk with no reasons; none achieved gave high risk with three
  reasons, using the release's own high-risk cut-off.

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
| TC009 | 24 to 59 month model, all milestones achieved | Child aged 48 months, 13 answers achieved | Low risk, no reasons, not sent to CHW, four domains shown | As expected (synthetic release and real release 1.1.0) | Pass | test_api_flow::test_whole_flow |
| TC010 | 24 to 59 month model, milestones not achieved | Child aged 48 months, 13 answers not achieved | Medium or high risk, top reasons as plain questions, sent to CHW | As expected (synthetic release; high risk on real release 1.1.0) | Pass | test_api_flow::test_whole_flow |
| TC011 | Under-24 model assessment | Child aged 9 months; all answers achieved, then none achieved | Under-24 questions only; low when achieved; medium or high and sent to CHW when not; movement and language explained; thinking and social areas reported as not assessed and never overwrite the milestone summary | As expected | Pass | test_api_flow::test_under_24_months_uses_the_under2_model |
| TC012 | Invalid answers | An answer outside the options; a missing question; an extra question | Refused, naming the missing or unexpected questions | As expected | Pass | test_api_flow::test_bad_answers_are_refused |
| TC013 | Youngest ages | Children aged 0 and 3 months; the same ages with the under-24 model unavailable | Assessed by the under-24 model; with the model unavailable, refused with a message to check from 4 months | As expected | Pass | test_inference::test_under2_model_covers_0_to_23, test_inference::test_ages_outside_coverage |
| TC021 | Fallback when the under-24 model is unavailable | Child aged 20 months, under-24 model files missing; then walking and standing alone not achieved | WHO motor check: six movement questions; low when achieved; high with two overdue milestones and months past the window | As expected | Pass | test_api_flow::test_under_24_months_uses_the_motor_milestone_check |
| TC022 | Under-24 questions follow the child's month | Every month from 0 to 23 | Between 1 and 15 questions, all from the under-24 short form | As expected | Pass | test_inference::test_under2_questions_follow_the_child_month |
| TC023 | Under-24 odd-answer check | Child aged 10 months: the hardest questions for the age answered yes, the easiest no | Report flagged as unusual for the CHW | As expected | Pass | test_inference::test_under2_contradictory_report_is_flagged, test_anomaly_under2::test_walking_without_sitting_is_flagged |

## CHW review and administration

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC014 | CHW records an outcome | Flagged result; outcome "refer to facility" | Case leaves the open list; caregiver sees the fixed referral message | As expected | Pass | test_api_flow::test_whole_flow |
| TC015 | "Unreachable" outcome | Flagged result; outcome "unreachable" | Outcome stored; no message shown to the caregiver | As expected | Pass | test_api_flow::test_unreachable_shows_the_caregiver_nothing |
| TC016 | Another CHW's case | CHW records an outcome on a case of a caregiver not linked to them | Refused (not found) | As expected | Pass | test_access::test_cases_and_outcomes_belong_to_the_linked_chw |
| TC017 | Usage summary | Two assessments (one low, one flagged), one outcome | Counts rise by exactly these amounts; a future date range shows none | As expected | Pass | test_admin::test_usage_summary_counts |
| TC018 | Deactivating a CHW with caregivers | CHW still linked to a caregiver | Refused until the caregiver is moved | As expected | Pass | test_admin::test_deactivation_rules |

## Mobile app

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC024 | Check saved when offline and sent later | Check finished with no connection; connection back; one saved check refused by the server | Answers kept on the phone; sent oldest first when back online; a refused check is dropped and the caregiver asked to redo it; checks are kept per account | As expected | Pass | app pending_check_test (7 tests) |
| TC025 | Under-24 result screen | Result with thinking and social areas not assessed | Only checked areas shown as cards; one line names the areas checked from 24 months; under-24 questions tagged Language or Movement | As expected | Pass | app under2_result_test (3 tests) |

## Model release integrity

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC019 | Altered release file | Release with a changed peer_stats.json; release with a missing file | Release refused (checksum; missing file) | As expected | Pass | ml test_export::test_altered_or_missing_file_is_refused |
| TC020 | Synthetic release in production | DEV_MODE=false with a synthetic release | API refuses to serve it | As expected | Pass | test_inference::test_synthetic_release_is_refused_outside_development |

## Performance

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC026 | API response time | 150 assessments on a local server: 50 at 40 months (release 1.0.0), 100 at 18 and 9 months (under-24 model) | Server work for one assessment well within the 3 second target | Median: questions 0.02 s; submit 0.18 s (24 to 59 model), 0.10 s (under-24 model). 95th percentile at most 0.51 s. Estimated end to end: 2.4 s on Fast 3G (within target), 8.2 s on Slow 3G (not within target; network time) | Pass (server); limitation on Slow 3G | backend/scripts/measure_latency.py, results in latency_2026-11-09.md |

TC026 was measured with release 1.0.0, which has the same model as 1.1.0 and differs only
in the high-risk cut-off, so its timings carry over. Slow 3G times are estimates from
response sizes and standard network figures, not measurements on a phone; the offline
save and retry (TC024) covers checks that cannot be sent in time.
