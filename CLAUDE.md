# Agy Cloud Bridge

Python bridge that lets you chat with Agy or Claude Code from a Markdown file
in a synced cloud folder (iCloud Drive, Dropbox). It watches `agy-chats/` and
`claude-chats/`, sends the file to the matching CLI when a line reads `.end`,
and streams the reply back into the file. See `README.md` for setup and the
LaunchAgent.

- Everything is in `agy_bridge.py`. The `test_*.py` and `pty_test.py` files
  are manual experiments, not a test suite.
- File rewrites must stay atomic (write to a temp file, then replace), so a
  crash can't corrupt a chat.
- The user's cloud-folder choice is stored in `~/.agy_bridge_config.json`;
  never commit it.
