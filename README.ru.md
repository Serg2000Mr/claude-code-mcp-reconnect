# Claude Code MCP Auto-Reconnect Patch

[**English version**](README.md)

Вы разрабатываете или дорабатываете MCP-сервер. После пересборки MCP-сервера все открытые чаты Claude Code показывают устаревший список инструментов.
Вам приходится постоянно делать одну из следующих операций.
 * перезагружать VS Code
 * Ctrl-Shift-P -> Developer: Reload Window
 * выполнять команду /mcp и нажимать Reconnect на нужном MCP-сервере. И это действует только в одном чате.

Это вынуждает постоянно присутствовать при процессе разработки и двигать процесс вручную
 
Данный патч делает переподключение автоматическим: скрипт сборки изменяет файл-флаг, и все открытые чаты обновляют нужный MCP-сервер за 2 секунды.

> **Платформа**: Windows, VSCode. Проверено на Claude Code v2.1.87–v2.1.89.

---

## Быстрый старт

**1. Настроить** — отредактировать две строки вверху `apply_patch.py`:

```python
SERVER_NAME = "your-mcp-server-name"     # из .vscode/settings.json → mcp → servers
FLAG_FILE   = r"C:\path\to\your\.mcp-reconnect"
```

**2. Пропатчить** — запустить один раз, затем перезагрузить VSCode (`Ctrl+Shift+P` → Developer: Reload Window):

```bash
python apply_patch.py
```

**3. Триггер из скрипта сборки** — добавить в конец после успешной пересборки:

```bash
touch /path/to/.mcp-reconnect
```

**4. Проверить** — открыть Output → Claude Code: Show Logs. После следующей сборки:

```
[patch] All N channels reconnected OK
```

---

## Как это работает

Claude Code VSCode игнорирует `notifications/tools/list_changed` от MCP-серверов ([issue #4118](https://github.com/anthropics/claude-code/issues/4118)).
Это заявленная, но нерабочая способность. 

Патч встраивает IIFE в `extension.js`:

```
setInterval(2000ms)
  └── изменился mtimeMs файла-флага?
      └── да → Z.allComms (все открытые чаты)
                  └── reconnectMcpServer(channelId, serverName)
```

**Стабильные идентификаторы** (не минифицируются, сохраняются при обновлениях):
`allComms`, `reconnectMcpServer`

**Что может измениться при обновлении**: минифицированные переменные в якоре вставки (`K`, `Z`, `M6`). При изменении скрипт сообщает об этом явно — адаптация занимает несколько минут.

---

## Поддержание патча актуальным

Claude Code обновляется автоматически и стирает патч. Добавьте проверку в скрипт сборки:

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

Если выводит `NEEDS PATCH`: запустить `apply_patch.py` заново + Reload Window.

Перед повторным патчем проверьте, не вышел ли нативный фикс — тогда патч больше не нужен:

```bash
gh api repos/anthropics/claude-code/releases/latest --jq '.body' | grep -i mcp
```

---

## Адаптация к новой версии расширения

Если `apply_patch.py` выводит `ERROR: anchor not found`:

1. Открыть `extension.js` (путь выводится скриптом)
2. Найти строку, содержащую одновременно `allComms` и `onDidChangeConfiguration`
3. Обновить `ANCHOR` в `apply_patch.py` — скопировать начало этой строки
4. Запустить скрипт снова

### История якорей

| Версия | Якорь |
|--------|-------|
| v2.1.87 | `K.subscriptions.push(Z),K.subscriptions.push(O6.workspace.onDidChangeConfiguration` |
| v2.1.88+ | `K.subscriptions.push(Z),K.subscriptions.push(M6.workspace.onDidChangeConfiguration` |

Структурный паттерн (`subscriptions.push(Z)` + `onDidChangeConfiguration`) стабилен с v2.1.87. Менялась только минифицированная переменная пространства имён.

---

## Ограничения

- Только Windows
- Стирается при каждом обновлении расширения Claude Code
- На VSCode Insiders и Cursor не тестировалось
