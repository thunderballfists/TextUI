# Log selection and clipboard implementation plan

1. Add failing behavioral tests for `on-selection-ended`, including pointer release outside the log and content updates after a selection.
2. Add `TranscriptLog.SelectionEnded`, subscribe to the screen's native `TextSelected` event, register its markup event, and explicitly forward it in convenience Apps.
3. Add failing clipboard tests with mocked platform discovery and asynchronous subprocesses. Implement fixed executable candidates, Unicode stdin, timeout/cancellation cleanup, native backend reporting, and OSC 52 supplementation.
4. Expose the helper from the package and through `window.copy`; test lifecycle behavior.
5. Opt the showcase into copy-on-selection through a controller action. Update runtime/controls docs, README, and changelog.
6. Run focused tests, full headless suite, visual checks, Pyflakes, lockfile/build checks, and independent review. Create a PR for #78, inspect feedback, and resolve verified findings before merging.
