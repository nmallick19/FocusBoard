# Focusboard

Local Ubuntu desktop app for reminders and task tracking. Add tasks on a calendar, see all open work plus what is due today / in the next 3 days / in the next 7 days, track time from Start to Finish, and keep a logbook of what you completed or missed.

Data stays on your machine (`~/.local/share/focusboard/focusboard.db`). No accounts, no cloud.

## Install

```bash
cd ~/apps/focusboard
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
source ~/apps/focusboard/.venv/bin/activate
python -m focusboard
```

Or, after the venv is on your `PATH`:

```bash
focusboard
```

On first launch the app:

- opens the main window
- puts a Focusboard icon in the top bar (system tray)
- installs a menu entry under **Focusboard**
- can start at login from the tray or **File → Start at login**

Close the main window to hide it; the top-bar icon keeps the app running. Click the icon to see All / Today / 3-day / 7-day tasks. Quit from the tray or **File → Quit**. Starting Focusboard again closes the previous instance first, so only one copy runs.

## What it does

- **Focus** — All tasks, Today (overdue + today), Tomorrow to +3 days, and Days 4–7 (no overlap). Tick **Next**, **Ongoing**, and/or **Finished**. Unticking all three snaps back to Next+Ongoing.
- **Calendar** — month view; days with tasks are highlighted; add or edit by day
- **Logbook** — completed and missed tasks for the selected week, with duration, estimate, and delay reason
- **Top bar** — click the icon for **Reminders** (due today and due in 3 days, with times), then All / Today / 3-day / 7-day lists, new task, theme, autostart, and quit
- **Theme** — **File → Theme** or the tray menu: System (default, follows Ubuntu light/dark), Light, or Dark. The choice is remembered.
- **Reminders** — while the app is running, it checks once a minute. On the first check each day you get a “What needs doing” digest (today + next 3 days). When a task’s due time is reached you get “Task due”. Ongoing work pings again after 2 hours. Changing a due time arms a new due notification.
- **Undo** — **Undo Start** returns Ongoing → Next. **Reopen** returns Finished or Missed → Next.

Statuses: **To do** (Next) → **Ongoing** (Start) → **Done** (Finish). Duration is the time between Start and Finish. If you finish after the deadline, or mark a task **Missed**, you pick a reason.

## Ubuntu notes

- GNOME may hide tray icons unless [AppIndicator / Ubuntu AppIndicators](https://extensions.gnome.org/) is enabled. Notifications still work via `notify-send`.
- Autostart writes `~/.config/autostart/focusboard.desktop` pointing at the Python used to launch the app (your venv).

## Uninstall

```bash
rm -f ~/.config/autostart/focusboard.desktop
rm -f ~/.local/share/applications/focusboard.desktop
rm -f ~/.local/share/icons/hicolor/scalable/apps/focusboard.svg
# optional: delete your tasks
rm -rf ~/.local/share/focusboard
```
