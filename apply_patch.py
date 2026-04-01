"""
Inject MCP auto-reconnect IIFE into Claude Code extension.js (VSCode, Windows)

Configure SERVER_NAME and FLAG_FILE below, then run:
    python apply_patch.py

After running: Ctrl+Shift+P → Developer: Reload Window
See README.md for full usage and update procedure.
"""
import sys
import glob
import os
import re
import shutil

# ---- configure these ----
SERVER_NAME = "your-mcp-server-name"       # MCP server name from .vscode/settings.json
FLAG_FILE   = r"C:\path\to\your\.mcp-reconnect"  # build script touches this file
# -------------------------

def js_str(s):
    """Escape a value for embedding inside a JS double-quoted string literal."""
    return s.replace('\\', '\\\\').replace('"', '\\"')

EXT_DIR = os.path.expandvars(r"%USERPROFILE%\.vscode\extensions")
candidates = glob.glob(os.path.join(EXT_DIR, "anthropic.claude-code-*-win32-x64"))
if not candidates:
    sys.exit(f"ERROR: Claude Code extension not found in {EXT_DIR}")

def version_key(path):
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', os.path.basename(path))
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

EXT_JS = os.path.join(max(candidates, key=version_key), "extension.js")
print(f"Target: {EXT_JS}")

# Anchor: right after Z (allComms manager) is pushed to subscriptions.
# Update ANCHOR when the extension updates — see README for how to find the new one.
ANCHOR = "K.subscriptions.push(Z),K.subscriptions.push(M6.workspace.onDidChangeConfiguration"

PATCH = (
    '/* --- MCP auto-reconnect patch --- */'
    '(function(){'
    'var fs=require("fs");'
    f'var flagPath="{js_str(FLAG_FILE)}";'
    f'var serverName="{js_str(SERVER_NAME)}";'
    'var lastTs=0;'
    'try{lastTs=fs.statSync(flagPath).mtimeMs}catch(e){}'
    'var inFlight=false,pendingTs=0,retries=0;'
    'var h=setInterval(function(){'
    'if(inFlight)return;'
    'try{'
    'var ts=fs.statSync(flagPath).mtimeMs;'
    'if(ts<=lastTs)return;'
    'var comms=Array.from(Z.allComms);'
    'if(!comms.length)return;'
    'if(ts!==pendingTs){pendingTs=ts;retries=0;}'
    'inFlight=true;'
    'var p=[];'
    'comms.forEach(function(c){'
    'if(c.channels&&c.channels.size)'
    'c.channels.forEach(function(_,id){p.push(c.reconnectMcpServer(id,serverName));});'
    '});'
    'Promise.allSettled(p).then(function(r){'
    'inFlight=false;'
    'var fail=r.filter(function(x){return x.status==="rejected";}).length;'
    'if(!fail){lastTs=pendingTs;console.log("[patch] All "+r.length+" channels reconnected OK");}'
    'else if(++retries>=3){lastTs=pendingTs;console.log("[patch] "+fail+"/"+r.length+" channels failed after 3 retries — tools may be stale. Open Output > Claude Code: Show Logs.");}'
    'else{console.log("[patch] "+fail+"/"+r.length+" channels failed, retrying ("+retries+"/3)...");}'
    '});'
    '}catch(e){console.log("[patch] error: "+e);}'
    '},2000);'
    'K.subscriptions.push({dispose:function(){clearInterval(h);}});'
    '})();'
    '/* --- end patch --- */'
)

MARKER = "MCP auto-reconnect patch"

with open(EXT_JS, encoding="utf-8") as f:
    content = f.read()

if MARKER in content:
    sys.exit("Already patched — skipping.")

if ANCHOR not in content:
    sys.exit(
        "ERROR: anchor not found.\n"
        "The extension was updated. Find new anchor by searching extension.js for a line\n"
        "containing both 'allComms' and 'onDidChangeConfiguration', then update ANCHOR above.\n"
        "See README.md for the full procedure."
    )

backup = EXT_JS + ".bak"
shutil.copy2(EXT_JS, backup)
print(f"Backup: {backup}")

patched = content.replace(ANCHOR, PATCH + ANCHOR, 1)

with open(EXT_JS, "w", encoding="utf-8") as f:
    f.write(patched)

old_size, new_size = len(content), len(patched)
print(f"Patch applied at position {content.find(ANCHOR)}")
print(f"File size: {old_size} -> {new_size} (+{new_size - old_size} bytes)")
print("Next: Ctrl+Shift+P -> Developer: Reload Window")
print(f"To rollback: copy {backup} back to {EXT_JS}")
