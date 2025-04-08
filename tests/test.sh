#!/bin/bash
set -uo pipefail
source .venv/bin/activate

### run linters
# Determine pre-commit arguments based on script arguments
if [ $# -eq 0 ]; then
    PRE_COMMIT_ARGS="--all-files"
else
    PRE_COMMIT_ARGS="--files $*"
fi

# Run pre-commit, capture output, and allow for a second run if the first modifies files
output=$(pre-commit run $PRE_COMMIT_ARGS)
exit_code=$?

if [ $exit_code -eq 0 ]; then
    # First run succeeded, print its output
    echo "$output"
else
    # First run failed (likely modified files), run again and show output
    pre-commit run $PRE_COMMIT_ARGS || exit $?
fi

### run unit tests
pytest
