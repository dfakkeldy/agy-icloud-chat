# iCloud AI Bridge

A lightweight Python bridge that lets you chat with **Agy** or **Claude Code** from any Markdown editor on your iPhone, iPad, or Mac, using iCloud Drive as the sync mechanism.

## How It Works

The bridge monitors two folders inside your iCloud Documents (`~/Library/Mobile Documents/com~apple~CloudDocs/agy-icloud-chat/`):

| Folder | AI |
|---|---|
| `agy-chats/` | Agy |
| `claude-chats/` | Claude Code |

Create a `.md` file in the folder of the AI you want to talk to, type your message under the `**User:**` tag, add `.end` on its own line, and hit Return — the AI replies in real-time.

## Features

- **Multi-AI Routing**: Each chat folder routes to its own AI binary with independent configuration.
- **True Conversation Memory**: The entire markdown file is passed as context. Edit or delete previous messages — the AI adapts natively.
- **Live Streaming**: Responses stream one character at a time and flush to iCloud every second, so you see the AI "type" in real-time.
- **Auto-Continuation**: After each response, a fresh `**User:**` tag is appended so you can immediately type your next message.
- **Artifact Syncing**: Generated images and local file artifacts are copied to `logs/assets/` and markdown links are rewritten so they display instantly on iOS.
- **Permissionless Mode**: All CLI tool calls are auto-approved — no terminal prompts block your chat.
- **Environment Bootstrapping**: Runs the CLI through a Zsh login shell that sources `~/.zshrc`, ensuring API keys are loaded. Maps `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY` for Claude Code compatibility.
- **Crash-Safe Writes**: All file truncations use atomic write-via-tempfile — a crash mid-write can't corrupt your chat history.
- **Hot Restart**: Type `.restart` in any chat file to restart the bridge process without touching the terminal.

## Sending a Message

1. Open (or create) a `.md` file in `agy-chats/` or `claude-chats/`.
2. Type your message under `**User:**`.
3. On a new line, type `.end` and press Return.
4. The bridge detects the `.end` marker, invokes the AI, and streams the response.

### Example

```markdown
# My Chat

**User:**
What is the capital of France?
.end
```

The bridge strips the `.end` marker, passes the full conversation as context, and writes the AI's response under `**Agy:**` or `**Claude:**`, followed by a fresh `**User:**` tag for your next prompt.

### Commands

| Command | Effect |
|---------|--------|
| `.end` | Triggers the AI to respond to your message |
| `.restart` | Restarts the bridge process (useful after updating `agy_bridge.py`) |

Commands are detected on their own line and stripped from the conversation before being sent to the AI.

## Frontmatter

Place control tags at the top of your markdown files:

```markdown
**Workspace:** /Users/yourname/Developer/my-project
**System Prompt:** Act as a senior iOS engineer. Be concise.

**User:**
Check out my latest code!
.end
```

| Tag | Effect |
|---|---|
| `**Workspace:** <path>` | Sets the working directory for the AI process |
| `**System Prompt:** <text>` | Prepends a system instruction to the conversation context |

If no workspace is specified, defaults to `~/`. If the workspace path doesn't exist, the bridge writes a warning to the chat file and falls back to `~/`.

## Directory Structure

```
~/Library/Mobile Documents/com~apple~CloudDocs/agy-icloud-chat/
├── agy-chats/
│   ├── Welcome.md          # Auto-created on first run if folder is empty
│   ├── *.md                # Your chat files
│   └── logs/
│       └── assets/         # Synced artifact files (images, etc.)
└── claude-chats/
    ├── Welcome.md
    ├── *.md
    └── logs/
        └── assets/
```

## Setup

1. **Python 3** required on your Mac. No external libraries needed.
2. Install **`agy`** and/or **`claude`** CLI tools at `~/.local/bin/`.
3. Grant **Full Disk Access** to `/usr/bin/python3` in `System Settings > Privacy & Security` — the bridge needs this to read your iCloud Drive.
4. Set up the **LaunchAgent** to run in the background (see below).

### Background Service (LaunchAgent)

Create `~/Library/LaunchAgents/com.yourname.agybridge.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.agybridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/agy_bridge.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/agy_bridge.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/agy_bridge.err</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.yourname.agybridge.plist
```

## Environment Variables

The bridge launches each AI through `/bin/zsh -c` with `source ~/.zshrc` to pick up your shell environment. For Claude Code, it also maps:

- `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY`

Make sure your API keys are exported in `~/.zshrc`.

## Architecture

```
agy_bridge.py
├── atomic_write()               # Write to temp file then os.replace() for crash-safe atomic writes
├── initialize_directories()     # Ensure folders, logs/, assets/ exist; create Welcome.md
├── main()                       # Poll iCloud dirs for .md file changes every 1s
│   └── parse_and_respond()      # Detect .end/.restart commands, invoke CLI, stream response
│       ├── extract_workspace()  # Parse **Workspace:** frontmatter, validate path exists
│       ├── extract_system_prompt()  # Parse **System Prompt:** frontmatter
│       └── process_artifacts()  # Copy generated files to logs/assets/, rewrite links atomically
```
