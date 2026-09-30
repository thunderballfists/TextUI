# Log selection completion and clipboard design

## Contract

`<log on-selection-ended="copy_selection"/>` exposes a native drag-completion event without polling. `TranscriptLog.SelectionEnded` carries the log, selected text, and native `Selection` coordinates. It is emitted for nonempty log selections in response to Textual's public `TextSelected` event, including drags released outside the log. Native `MouseDown` marks new gestures; retained selection objects are ignored on scrollbar releases. Ordinary redraws and streamed text updates do not emit completion events. Copying remains an explicit action.

`await window.copy(text)` delegates to exported `await copy_to_clipboard(app, text)`. It tries a platform clipboard executable asynchronously, then also sends Textual's OSC 52 transport. The return value names the successful native backend (`pbcopy`, `clip`, `wl-copy`, `xclip`, or `xsel`) or `osc52` when only the terminal transport was sent. This is transport reporting, not confirmation that the terminal accepted OSC 52. Window copying requires the ready phase.

## Implementation boundaries

Use fixed argument vectors without a shell; clipboard text goes only to stdin. Native subprocesses have a two-second timeout per candidate and are killed and reaped on timeout or cancellation. Failed or unavailable tools fall through. macOS receives UTF-8 with an explicit UTF-8 locale; Windows `clip` receives UTF-16LE with a BOM; Linux tools receive UTF-8, preferring Wayland when its display is present. No dependencies are added. Native Textual copy shortcuts are unchanged.

## Verification

Pilot tests cover completion timing, exact selected text, repeat gestures, no notification on content updates, and release outside the log. Mock subprocess tests cover candidate order, Unicode payloads, failure, timeout, cancellation cleanup, and OSC 52 fallback without touching the developer's clipboard. A project-runtime test covers the window facade and ready-phase guard. The showcase opts in through an action and reports the backend.
