# MacDock

Отдельный Dock для Hyprland: нативное размытие, увеличение иконок, анимации, автоскрытие и закрепления.
Основан на MacShell; исходная MIT-лицензия сохранена. Подробности: [README](README.md), [NOTICE](NOTICE).

## Требования

Quickshell 0.3.2, Python 3.11+, Qt 6 Quick/Effects/Multimedia, Hyprland, пользовательский systemd.
Для виджета управления — Noctalia 5.4.1 / Plugin API 42. Тема иконок устанавливается отдельно;
MacOS-Like поддерживается, но не поставляется с проектом.

## Установка

```sh
git clone https://github.com/Wenwu-PA/macshell-dock.git
cd macshell-dock
./install.sh --deps
./install.sh
qs -c MacDock
```

Команды выполняются обычным пользователем; --deps вызывает pacman через sudo.
При работающей Noctalia: `./install.sh --plugin`. Затем добавьте **MacDock Control** через редактор виджетов Bar.
Виджет открывает единственную компактную панель. Установщик сам не меняет расположение виджетов.
Настройки — ~/.config/macdock/settings.json, закрепления — pinned.json. Они не включены в репозиторий.

## Обновление и удаление

```sh
git pull --ff-only
./install.sh --plugin-update
```

Обновление требует IPC работающей Noctalia, создаёт резервную копию и откатывается при неудачной проверке.
Не заменяйте один манифест отдельно от других компонентов. Неизвестные локальные правки блокируют обновление.
Для удаления интеграции: `./install.sh --plugin-remove`, затем удалите виджет через редактор Bar.
Для удаления Dock: `~/.local/bin/macdock stop`, затем `./uninstall.sh`. Настройки и закрепления сохраняются.

## Проверки и ограничения

```sh
python3 tools/check.py
noctalia plugins lint noctalia/plugin
```

Проверены автоматические тесты и offscreen-анимация. Реальные Native Blur, появление Dock, быстрый hover,
NVIDIA, два монитора и взаимодействие с виджетом требуют отдельной проверки в Hyprland.
Эта подготовка v0.1.0 не является подтверждением графической готовности. Проверенного скриншота пока нет.
Никаких экспериментальных сборок Noctalia, захвата обоев и изменения глобальной силы blur.

Диагностика: [Troubleshooting](docs/TROUBLESHOOTING.md). Публичный Release до завершения приёмки не опубликован.
