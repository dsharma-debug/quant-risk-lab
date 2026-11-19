# Changelog

## Initial review package

- Consolidated the complete pricing, risk, hedging, research and dashboard code.
- Added a project README, architecture, reproduction, findings and setup guides.
- Added dependency specifications and a GitHub Actions test workflow.
- Added reproduce.py with command logs, version records and source/output hashes.
- Retained the latest seed-7 Monte Carlo demonstration; seed/sample counts are
  now command-line options. Tree comparison counts are also configurable.
- Consolidated delta experiment outputs under results/.
- Retained the numerical algorithms and their established accounting conventions.
- Included reference summaries and figures; detailed trial outputs are regenerated.

The earlier incremental tutorial files are replaced by named documentation in
docs/. This package is a fresh copy; it does not modify the original working folder.
