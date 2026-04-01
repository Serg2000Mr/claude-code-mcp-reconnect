# Claude Code MCP Auto-Reconnect Patch

[**English version**](README.md)

Обходное решение для [anthropics/claude-code#4118](https://github.com/anthropics/claude-code/issues/4118): расширение Claude Code для VSCode игнорирует уведомление `notifications/tools/list_changed` от MCP-серверов. После пересборки MCP-сервера все открытые чаты показывают устаревший список инструментов — до тех пор, пока вручную не выполнить `/mcp` → Reconnect в каждой вкладке.

Патч встраивает IIFE в `extension.js`: следит за файлом-флагом и автоматически вызывает `reconnectMcpServer`. Скрипт сборки делает `touch .mcp-reconnect` — и все открытые чаты переподключаются в течение 2 секунд.

> **Платформа**: только Windows (проверено на VSCode + Claude Code v2.1.87–v2.1.89).

---

## Как работает

```
скрипт сборки
  └── touch .mcp-reconnect          ← сигнал «сервер пересобран»

extension.js (пропатченный)
  └── setInterval(2000ms)
        ├── mtimeMs файла .mcp-reconnect изменился?
        └── да → перебираем Z.allComms (все открытые чаты)
                    └── reconnectMcpServer(channelId, serverName)
```

**Стабильные идентификаторы** (не минифицируются, сохраняются при обновлениях):
- `allComms` — `Set` всех активных чатов
- `reconnectMcpServer(channelId, name)` — API переподключения

**Что может измениться при обновлении**: минифицированные имена переменных в якоре вставки (`K`, `Z`, `M6`). При изменении скрипт сообщает об ошибке явно — адаптация занимает несколько минут (см. [Когда расширение обновляется](#когда-расширение-обновляется)).

---

## Установка

### 1. Настроить `apply_patch.py`

Отредактировать две переменные вверху файла:

```python
SERVER_NAME = "your-mcp-server-name"       # из .vscode/settings.json → mcp → servers
FLAG_FILE   = r"C:\path\to\your\.mcp-reconnect"
```

### 2. Применить патч

```bash
python apply_patch.py
```

Затем перезагрузить VSCode: `Ctrl+Shift+P` → **Developer: Reload Window**

### 3. Добавить в скрипт сборки

```bash
# в конце скрипта сборки, после успешной пересборки:
touch /path/to/.mcp-reconnect
```

### 4. Проверить

Открыть **Claude Code: Show Logs** (панель Output). После следующей сборки должно появиться:

```
[patch] All N channels reconnected OK
```

---

## Обнаружение обновлений расширения

Патч стирается при автообновлении Claude Code. Добавьте эту проверку в скрипт сборки:

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

Если выводит `NEEDS PATCH`: запустить `apply_patch.py` + Reload Window.

Перед повторным патчем стоит проверить release notes — если Anthropic выпустил нативный фикс, патч больше не нужен:

```bash
gh api repos/anthropics/claude-code/releases/latest --jq '.body' | grep -i mcp
```

---

## Когда расширение обновляется

Если `apply_patch.py` выводит `ERROR: anchor not found`:

1. Открыть `extension.js` (путь выводится скриптом)
2. Найти строку, содержащую одновременно `allComms` и `onDidChangeConfiguration`
3. Скопировать начало этой строки вплоть до `onDidChangeConfiguration` включительно
4. Обновить `ANCHOR` в `apply_patch.py`
5. Запустить скрипт снова

### История якорей

| Версия | Фрагмент якоря |
|--------|---------------|
| v2.1.87 | `K.subscriptions.push(Z),K.subscriptions.push(O6.workspace.onDidChangeConfiguration` |
| v2.1.88+ | `K.subscriptions.push(Z),K.subscriptions.push(M6.workspace.onDidChangeConfiguration` |

Изменилась только минифицированная переменная пространства имён (`O6` → `M6`). Структурный паттерн — `subscriptions.push(Z)` за которым следует `onDidChangeConfiguration` — стабилен начиная с v2.1.87.

---

## Файлы

| Файл | Назначение |
|------|-----------|
| `apply_patch.py` | Скрипт применения патча, запускать повторно после каждого обновления расширения |
| `.mcp-reconnect` | Файл-флаг (добавить в .gitignore); важно только его mtimeMs |

---

## Ограничения

- Только Windows (использует соглашения пути `%USERPROFILE%`)
- Патчирует установленное расширение на месте; стирается при каждом обновлении Claude Code
- Проверено на VSCode; на VSCode Insiders и Cursor не тестировалось
