# Claude Code MCP Auto-Reconnect Patch

[**Русская версия**](README.ru.md)

After rebuilding your MCP server, all open Claude Code chats show stale tools until you manually reconnect each tab. This patch makes reconnect automatic — your build script touches a flag file and all open chats refresh within 2 seconds.

> **Platform**: Windows, VSCode. Tested on Claude Code extension v2.1.87–v2.1.89.

---

## Quick start

**1. Configure** — edit two lines at the top of `apply_patch.py`:

```python
SERVER_NAME = "your-mcp-server-name"     # from .vscode/settings.json → mcp → servers
FLAG_FILE   = r"C:\path\to\your\.mcp-reconnect"
```

**2. Patch** — run once, then reload VSCode (`Ctrl+Shift+P` → Developer: Reload Window):

```bash
python apply_patch.py
```

**3. Trigger from your build script** — add at the end, after a successful rebuild:

```bash
touch /path/to/.mcp-reconnect
```

**4. Verify** — open Output → Claude Code: Show Logs. After the next rebuild:

```
[patch] All N channels reconnected OK
```

---

## Background

Claude Code VSCode ignores `notifications/tools/list_changed` from MCP servers ([issue #4118](https://github.com/anthropics/claude-code/issues/4118)). The workaround patches `extension.js` directly with an IIFE:

```
setInterval(2000ms)
  └── flag file mtime changed?
      └── yes → Z.allComms (all open chats)
                  └── reconnectMcpServer(channelId, serverName)
```

**Stable identifiers** (not minified, survive extension updates):
`allComms`, `reconnectMcpServer`

**What can change on update**: minified variable names in the injection anchor (`K`, `Z`, `M6`). The script fails with a clear error — adapting takes a few minutes.

---

## Keeping the patch alive

Claude Code auto-updates and wipes the patch. Add this check to your build script:

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

If it prints `NEEDS PATCH`: re-run `apply_patch.py` + Reload Window.

Before re-patching, check if Anthropic shipped a native fix — if so, the patch is no longer needed:

```bash
gh api repos/anthropics/claude-code/releases/latest --jq '.body' | grep -i mcp
```

---

## Adapting to a new extension version

If `apply_patch.py` prints `ERROR: anchor not found`:

1. Open `extension.js` (path is printed by the script)
2. Search for a line containing both `allComms` and `onDidChangeConfiguration`
3. Update `ANCHOR` in `apply_patch.py` to match that line's beginning
4. Re-run the script

### Anchor history

| Version | Anchor |
|---------|--------|
| v2.1.87 | `K.subscriptions.push(Z),K.subscriptions.push(O6.workspace.onDidChangeConfiguration` |
| v2.1.88+ | `K.subscriptions.push(Z),K.subscriptions.push(M6.workspace.onDidChangeConfiguration` |

The structural pattern (`subscriptions.push(Z)` + `onDidChangeConfiguration`) has been stable since v2.1.87. Only the minified namespace variable changed.

---

## Limitations

- Windows only
- Wiped on every Claude Code extension update
- Not tested on VSCode Insiders or Cursor
