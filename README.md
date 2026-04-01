# Claude Code MCP Auto-Reconnect Patch

[**Русская версия**](README.ru.md)

A workaround for [anthropics/claude-code#4118](https://github.com/anthropics/claude-code/issues/4118): Claude Code VSCode extension ignores `notifications/tools/list_changed` from MCP servers, so after rebuilding your MCP server all open chats show stale tools until you manually run `/mcp` → Reconnect in every tab.

This patch injects an IIFE into `extension.js` that watches a flag file and calls `reconnectMcpServer` automatically — your build script just does `touch .mcp-reconnect` and all open chats reconnect within 2 seconds.

> **Platform**: Windows only (tested on VSCode + Claude Code extension v2.1.87–v2.1.89).

---

## How it works

```
build script
  └── touch .mcp-reconnect          ← signals "server rebuilt"

extension.js (patched)
  └── setInterval(2000ms)
        ├── stat(.mcp-reconnect).mtimeMs changed?
        └── yes → iterate Z.allComms (all open chats)
                    └── reconnectMcpServer(channelId, serverName)
```

**Stable identifiers** (not minified, survive extension updates):
- `allComms` — `Set` of all active chat instances
- `reconnectMcpServer(channelId, name)` — reconnect API

**What can change on update**: minified variable names in the injection anchor (`K`, `Z`, `M6`). The script fails clearly if the anchor isn't found — adapting takes a few minutes (see [When the extension updates](#when-the-extension-updates)).

---

## Setup

### 1. Configure `apply_patch.py`

Edit the two variables at the top:

```python
SERVER_NAME = "your-mcp-server-name"       # from .vscode/settings.json → mcp → servers
FLAG_FILE   = r"C:\path\to\your\.mcp-reconnect"
```

### 2. Apply the patch

```bash
python apply_patch.py
```

Then reload VSCode: `Ctrl+Shift+P` → **Developer: Reload Window**

### 3. Add to your build script

```bash
# at the end of your build script, after a successful rebuild:
touch /path/to/.mcp-reconnect
```

### 4. Verify

Open **Claude Code: Show Logs** (Output panel). After the next rebuild you should see:

```
[patch] All N channels reconnected OK
```

---

## Detecting extension updates

The patch is wiped when Claude Code auto-updates. Add this check to your build script:

```bash
python -c "
import glob, os, re
d = os.path.expandvars(r'%USERPROFILE%\.vscode\extensions')
c = glob.glob(os.path.join(d, 'anthropic.claude-code-*-win32-x64'))
def vk(p): m=re.search(r'(\d+)\.(\d+)\.(\d+)',os.path.basename(p)); return tuple(int(x) for x in m.groups()) if m else (0,0,0)
f = os.path.join(max(c,key=vk),'extension.js')
print('OK' if 'MCP auto-reconnect patch' in open(f).read() else 'NEEDS PATCH: '+f)
"
```

If it prints `NEEDS PATCH`: run `apply_patch.py` + Reload Window.

Also check the release notes before re-patching — if Anthropic ships a native fix, the patch is no longer needed:

```bash
gh api repos/anthropics/claude-code/releases/latest --jq '.body' | grep -i mcp
```

---

## When the extension updates

If `apply_patch.py` prints `ERROR: anchor not found`:

1. Open `extension.js` (path is printed by the script)
2. Search for a line containing both `allComms` and `onDidChangeConfiguration`
3. Copy that line's beginning up to and including `onDidChangeConfiguration`
4. Update `ANCHOR` in `apply_patch.py`
5. Run the script again

### Anchor history

| Version | Anchor fragment |
|---------|----------------|
| v2.1.87 | `K.subscriptions.push(Z),K.subscriptions.push(O6.workspace.onDidChangeConfiguration` |
| v2.1.88+ | `K.subscriptions.push(Z),K.subscriptions.push(M6.workspace.onDidChangeConfiguration` |

Only the minified namespace variable changed (`O6` → `M6`). The structural pattern — `subscriptions.push(Z)` followed by `onDidChangeConfiguration` — has been stable since v2.1.87.

---

## Files

| File | Purpose |
|------|---------|
| `apply_patch.py` | One-time patch script, re-run after each extension update |
| `.mcp-reconnect` | Flag file (gitignore it); only its mtime matters |

---

## Limitations

- Windows only (uses `%USERPROFILE%` path convention)
- Patches the installed extension in-place; wiped on every Claude Code update
- Tested on VSCode; not tested on VSCode Insiders or Cursor
