# Preparing a local Git repository

Use the clean release folder as a new project copy. Keep your earlier working
folder as a backup. The release contains the complete program, professional
documentation names and compact reference outputs. It does not contain your
virtual environment or a pre-existing .git history.

After verifying the release locally, initialize version control from its root:

```bash
git init -b main
git add .
git status
git commit -m "Add option pricing and hedging research platform"
```

If an older Git does not support the first command, use git init followed by
git branch -M main. If Git asks for author identity, set your own name and
preferred commit email; no identity has been configured for you in this copy.

The ignore rules keep virtual environments, Python caches, local secrets,
machine-specific dependency records, detailed trial CSVs and command logs out
of automatic staging. Compact summary CSVs and plots are included as reviewable
examples. Detailed trials are reproducible with reproduce.py.

The workflow under .github/workflows runs unit tests on Python 3.9/3.12 and
headless UI checks on Python 3.12 once installed in a GitHub repository. It has
not been executed remotely while preparing this release. There is no badge
claiming a successful remote run.

Creating a remote repository and pushing the commit are separate actions.
This package does not create, publish or modify a GitHub repository, and it
contains no remote URL or credentials. Repository name, visibility and licensing
can be chosen when the project is ready to share.
