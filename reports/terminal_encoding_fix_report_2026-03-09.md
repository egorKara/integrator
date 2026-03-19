# Terminal Encoding Fix Report — 2026-03-09

## Инцидент
- В `Terminal#1-6` наблюдались кракозябры в prompt-сообщении при вводе секрета.
- В `Terminal#3-19` pipeline падал при direct curl timeout.

## Причины
1. Текст prompt на кириллице в контексте текущей кодировки shell давал нечитаемый вывод.
2. Timeout direct-check воспринимался как фатальная ошибка выполнения.

## Исправления
- `set_proxy_secret_credman.ps1`:
  - включён UTF-8 режим консоли;
  - prompt переведён в ASCII/English.
- `run_win10_proxy_pipeline.ps1`:
  - direct-check выполнен в soft-fail режиме через `Invoke-CurlCapture`;
  - добавлены поля `VERIFY_DIRECT_EXIT`, `VERIFY_PROXY_EXIT`, `VERIFY_IPINFO_EXIT`.
- Добавлен helper:
  - `C:\integrator\set_terminal_utf8.ps1`.

## Верификация
- Новый pipeline лог: `C:\integrator\reports\win10_proxy_pipeline_20260309_161239.log`
- Результат: direct timeout (`VERIFY_DIRECT_EXIT=28`) не прерывает сценарий, proxy-verify остаётся `OK`.

## Операционный workaround
1. Перед интерактивным вводом секрета выполнить:
   - `powershell -ExecutionPolicy Bypass -File C:\integrator\set_terminal_utf8.ps1`
2. Затем выполнять:
   - `set_proxy_secret_credman.ps1`
   - `run_win10_proxy_pipeline.ps1`
