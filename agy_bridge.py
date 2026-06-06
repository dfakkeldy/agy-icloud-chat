import os
import time
import subprocess
import logging
import re
import shutil
import sys
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

COMMAND_DETECT_REGEX = re.compile(r'(?m)^\.(end|restart)[ \t]*\n*[ \t]*$')
COMMAND_STRIP_REGEX = re.compile(r'\n*\.(end|restart)[ \t]*\n*$')

def strip_ansi_and_control(text):
    text = text.replace('\x04', '')
    text = text.replace('\x1b]0;', '')
    ANSI_ESCAPE = re.compile(r'''
        \x1B
        (?:
            [@-Z\\-_]
        |
            \[
            [0-?]*
            [ -/]*
            [@-~]
        |
            [()][A-Z0-9]
        |
            \].*?(?:\x07|\x1B\\)
        |
            [78c]
        )
    ''', re.VERBOSE)
    return ANSI_ESCAPE.sub('', text)

BASE_ICLOUD_DIR = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/agy-icloud-chat")

# Define the CLI configurations
CONFIGS = {
    "agy-chats": {
        "bin": os.path.expanduser("~/.local/bin/agy"),
        "flags": ["--dangerously-skip-permissions", "--print"],
        "tag": "**Agy:**",
        "name": "Agy"
    },
    "claude-chats": {
        "bin": os.path.expanduser("~/.local/bin/claude"),
        "flags": ["--permission-mode", "bypassPermissions", "--print", "--verbose"],
        "tag": "**Claude:**",
        "name": "Claude"
    }
}

def atomic_write(file_path, content):
    dir_name = os.path.dirname(file_path)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(temp_path, file_path)

def get_initial_content(bot_name):
    return f"""# {bot_name} Chat

Welcome to the {bot_name} iCloud Bridge! Type your message under the **User:** tag, type .end on a new line and hit Return to send, and {bot_name} will reply.
Optional: set a workspace directory or system prompt below.
**Workspace:** ~/Library/Mobile Documents/com~apple~CloudDocs/agy-icloud-chat/projects
**System Prompt:** You are a helpful assistant.

**User:** 
"""

def initialize_directories():
    for folder, config in CONFIGS.items():
        dir_path = os.path.join(BASE_ICLOUD_DIR, folder)
        logs_dir = os.path.join(dir_path, "logs")
        assets_dir = os.path.join(logs_dir, "assets")
        
        os.makedirs(dir_path, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(assets_dir, exist_ok=True)
        logging.info(f"Ensured directories exist: {dir_path}")
        
        md_files = [f for f in os.listdir(dir_path) if f.endswith('.md')]
        if not md_files:
            starter_file = os.path.join(dir_path, "Welcome.md")
            atomic_write(starter_file, get_initial_content(config["name"]))
            logging.info(f"Created initial chat file at {starter_file}")

def extract_workspace(content):
    match = re.search(r'\*\*Workspace:\*\*\s*(.+)', content)
    if match:
        path = os.path.expanduser(match.group(1).strip().strip('\'"'))
        if os.path.isdir(path):
            return path, True
        return path, False
    return os.path.expanduser("~/"), True

def extract_system_prompt(content):
    match = re.search(r'\*\*System Prompt:\*\*\s*(.+)', content)
    if match:
        return match.group(1).strip()
    return None

def process_artifacts(file_path, folder_name):
    try:
        dir_path = os.path.join(BASE_ICLOUD_DIR, folder_name)
        assets_dir = os.path.join(dir_path, "logs", "assets")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content = content
        
        for match in re.finditer(r'!\[.*?\]\((.+?)\)', content):
            raw_path = match.group(1)
            local_path = raw_path.replace("file://", "")
            
            if local_path.startswith("/") and os.path.exists(local_path):
                filename = os.path.basename(local_path)
                dest_path = os.path.join(assets_dir, filename)
                
                shutil.copy2(local_path, dest_path)
                logging.info(f"Copied artifact to {dest_path}")
                
                new_content = new_content.replace(raw_path, f"logs/assets/{filename}")
                
        if new_content != content:
            atomic_write(file_path, new_content)
            logging.info("Updated artifact links in markdown.")
            
    except Exception as e:
        logging.error(f"Error processing artifacts: {e}")

def parse_and_respond(file_path, folder_name):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return

    config = CONFIGS[folder_name]
    user_tag = "**User:**"
    bot_tag = config["tag"]
    bot_name = config["name"]
    
    last_user_idx = content.rfind(user_tag)
    if last_user_idx == -1:
        return
        
    last_bot_idx = content.rfind(bot_tag)
    
    if last_user_idx > last_bot_idx:
        raw_prompt = content[last_user_idx + len(user_tag):].lstrip()
        
        match = COMMAND_DETECT_REGEX.search(raw_prompt)
        if not match:
            return
            
        command = match.group(1)
        
        if command == "restart":
            logging.info(f"Restart command received in {os.path.basename(file_path)}. Restarting bridge...")
            content = COMMAND_STRIP_REGEX.sub('', content)
            atomic_write(file_path, content + f"\n\n**System:** Bridge restarted successfully.\n\n{user_tag} \n")
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        prompt_without_command = COMMAND_STRIP_REGEX.sub('', raw_prompt).strip()
        if not prompt_without_command:
            return
            
        logging.info(f"Triggering {bot_name} for {os.path.basename(file_path)}...")
        
        content = COMMAND_STRIP_REGEX.sub('', content)
        
        workspace_dir, is_valid_workspace = extract_workspace(content)
        if not is_valid_workspace:
            warning_msg = f"**System Warning:** Workspace path `{workspace_dir}` not found, falling back to `~/`."
            content += f"\n\n{warning_msg}"
            workspace_dir = os.path.expanduser("~/")

        sys_prompt = extract_system_prompt(content)
        
        think_instruction = "IMPORTANT: You MUST think out loud step-by-step and explain your reasoning BEFORE giving your final answer."
        if sys_prompt:
            sys_prompt += f" {think_instruction}"
        else:
            sys_prompt = think_instruction
            
        full_context = f"System Instruction: {sys_prompt}\n\n" + content
            
        atomic_write(file_path, content + f"\n\n{bot_tag}\n")
            
        try:
            # Explicitly source ~/.zshrc to ensure API keys are loaded, then run the CLI
            # We also map ANTHROPIC_AUTH_TOKEN to ANTHROPIC_API_KEY because Claude CLI specifically looks for the latter.
            zsh_command = f"source ~/.zshrc 2>/dev/null; export TERM=dumb; export NO_COLOR=1; export FORCE_COLOR=0; [ -n \"$ANTHROPIC_AUTH_TOKEN\" ] && export ANTHROPIC_API_KEY=\"$ANTHROPIC_AUTH_TOKEN\"; \"{config['bin']}\" {' '.join(config['flags'])} \"$1\""
            cmd = [
                "/bin/zsh", "-c",
                zsh_command,
                "--", full_context
            ]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                cwd=workspace_dir,
                bufsize=1
            )
            
            buffer = ""
            last_write_time = time.time()
            
            while True:
                char = process.stdout.read(1)
                if not char and process.poll() is not None:
                    break
                
                buffer += char
                
                if time.time() - last_write_time >= 1.0 and buffer:
                    esc_idx = buffer.rfind('\x1b')
                    if esc_idx != -1 and esc_idx >= len(buffer) - 20:
                        to_write = buffer[:esc_idx]
                        buffer = buffer[esc_idx:]
                    else:
                        to_write = buffer
                        buffer = ""
                        
                    if to_write:
                        cleaned = strip_ansi_and_control(to_write)
                        if cleaned:
                            with open(file_path, "a", encoding="utf-8") as f:
                                f.write(cleaned)
                                f.flush()
                    last_write_time = time.time()
                    
            if buffer:
                cleaned = strip_ansi_and_control(buffer)
                if cleaned:
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.write(cleaned)
                        f.flush()
                
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{user_tag} \n")
                f.flush()
                
            logging.info(f"Finished streaming response to {os.path.basename(file_path)}")
            
            process_artifacts(file_path, folder_name)
            
        except Exception as e:
            logging.error(f"Failed to run {bot_name}: {e}")
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"Error running {bot_name}: {e}")

def get_md_files():
    md_files = {}
    for folder in CONFIGS.keys():
        dir_path = os.path.join(BASE_ICLOUD_DIR, folder)
        try:
            for entry in os.scandir(dir_path):
                if entry.is_file() and entry.name.endswith('.md'):
                    md_files[entry.path] = (entry.stat().st_mtime, folder)
        except Exception as e:
            logging.error(f"Error scanning directory {dir_path}: {e}")
    return md_files

def main():
    initialize_directories()
    
    for config in CONFIGS.values():
        if not os.path.exists(config["bin"]):
            logging.error(f"{config['name']} executable not found at {config['bin']}")
            return
            
    logging.info(f"Watching {BASE_ICLOUD_DIR} subdirectories for changes...")
    
    last_mtimes = get_md_files()
    
    while True:
        try:
            current_mtimes_full = get_md_files()
            
            for file_path in list(current_mtimes_full.keys()):
                mtime, folder_name = current_mtimes_full[file_path]
                last_mtime = last_mtimes.get(file_path, (0, None))[0]
                
                if mtime > last_mtime:
                    parse_and_respond(file_path, folder_name)
            
            last_mtimes = get_md_files()
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping AI Bridge.")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
