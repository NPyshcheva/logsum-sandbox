# Comparison of Supervised vs. Async Agent Runs

## What both produced

Both runs achieved the same goal. They implemented the logsum feature from `spec.md`, added tests, configured CI, and created the required documentation: spec.md, src/logsum.py, data/sample_events.csv, data/summary.csv, tests/test_logsum.py, test-notes.md, questions.md, refactor-notes.md, except ci-notes.md( done by manual exacution)

## Where the agent saved time

The one-pass run was much faster because I only needed to provide one prompt instead of guiding each step. It generated code, tests, fixtures, performed a small refactoring, ran local tests, and updated the provenance file in a single run. My role was mostly reviewing the output.

## Where the agent went wrong or shorter

The one-pass run stopped after local work was complete. It didn't create a GitHub Pull Request or verify that GitHub CI passed. When I opened the PR, CI failed because Ruff found an unused `pytest` import. I had to review the logs, understand the issue, fix it, push the change, and wait for CI to pass before merging.

## What the agent did better

The agent created project structure quickly and kept code, tests, and documentation consistent. It also explained the CI failure in a way that was easy to understand, so fixing it didn't take much time.

## What I learned about supervised vs. async

I learned that the async approach is great for well-defined tasks because it completes a lot of work from a single prompt. At the same time, reviewing results is still important. Local tests passing doesn't always mean GitHub CI will also pass. Step-by-step work takes longer but helped me understand the overall workflow better.

## What I would do differently next time

Next time I would still choose the one-pass approach to save time, but I would ask the agent to include Git workflow tasks where possible. I would also check GitHub CI as soon as I open a PR instead of relying only on local test results.

I think this sounds more like a real reflection from someone with a QA background—clear, straightforward, and not overly polished. It also avoids repeating "the" and uses more natural phrasing like **"project structure"**, **"GitHub CI"**, and **"local work"** instead of constantly saying **"the project structure"**, **"the GitHub CI"**, etc.
