# Unicode-safe Testing

## Purpose

This repo frequently tests Chinese food names and payloads from Windows PowerShell.
The local shell path is easy to corrupt if non-ASCII text is embedded carelessly.

## Main rule

Do not assume inline Chinese literals are safe in PowerShell.

In this environment, PowerShell inline heredocs and one-liner literals may degrade non-ASCII text into `????` before the payload reaches Python or HTTP.

## Safe methods

Use one of these stable methods for non-ASCII test inputs:

- prefer Unicode escape literals such as `\\u70b8\\u6392\\u9aa8\\u4fbf\\u7576` when embedding payloads directly in scripts
- or write the payload to a UTF-8 file first, then read and send that file
- when writing JSON fixtures for scripts, prefer UTF-8 without BOM
- verify the final payload content before sending if the test depends on exact Chinese text

## BOM rule

If a JSON fixture fails before request dispatch because of an unexpected UTF-8 BOM, treat that as a test harness encoding failure.

Regenerate the file without BOM or read it with `utf-8-sig` before retrying.

## Invalid runs

Do not treat `????` inputs as valid evaluation results.

If the transport layer corrupted the text, the run is invalid and should be rerun with a Unicode-safe method.
