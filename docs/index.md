# SystemHub Documentation

SystemHub is a Windows desktop utility built in Python with a modern Tkinter interface. It combines system diagnostics, firewall management, and temporary-file cleanup in one place so you can inspect and optimize your machine without switching between several tools.

## What the project does

SystemHub helps you:

- view a live dashboard with CPU, RAM, storage and system information;
- inspect firewall rules and active connections;
- allow, block or remove firewall rules for specific ports;
- clean temporary files and common cache folders;
- export firewall rules to JSON, TXT or CSV files.

The tool is designed to be practical for everyday use, with a simple interface and clear actions for common diagnostics tasks.

## Main features

### Dashboard

The Dashboard page shows an overview of the system in real time:

- operating system and build;
- CPU name, model, usage, frequency and temperature;
- RAM total, usage and modules;
- disk usage, health and temperature when available;
- motherboard and BIOS information;
- GPU data when exposed by the environment.

The data is collected through a combination of:

- WMI;
- psutil;
- LibreHardwareMonitor when available;
- SMART-based disk information when supported.

### Firewall

The Firewall page allows you to manage Windows firewall settings directly from the app:

- check whether the firewall is enabled;
- enable or disable the firewall;
- view active connections with protocol, state, PID and process name;
- filter the list by port, protocol, process or address;
- allow or block a port;
- remove rules associated with a port;
- export firewall rules.

> Some firewall operations require administrator privileges.

### Cleanup

The Cleanup page tries to remove temporary files and common cache folders used by the system and installed apps. The process is conservative and avoids aggressive deletion of important data.

### Settings

The Settings page stores the app’s preferences and keeps the interface experience consistent.

## Requirements

- Python 3.10 or higher;
- Windows;
- administrator privileges for some firewall actions;
- the required Python libraries listed in requirements.txt.

## Installation

1. Open the terminal in the project folder.
2. Create and activate a virtual environment if you want an isolated setup.
3. Install the dependencies:

```bash
py -3 -m pip install -r requirements.txt
```

4. If you want hardware sensor monitoring to work better, place the LibreHardwareMonitor library in the project folder or in the modules folder.

## How to run

Run the app with:

```bash
py -3 main.py
```

The interface opens as a desktop application and loads the dashboard automatically.

## How to use the app

### 1. Start the app

Launch the program and wait for the dashboard to load. The initial collection can take a few seconds.

### 2. Review the dashboard

Use the Dashboard page to inspect the current state of the hardware and the operating system.

### 3. Manage firewall rules

Open the Firewall page to:

- check current firewall status;
- filter connections;
- allow or block ports;
- refresh the list after changes.

### 4. Clean temporary files

Open the Cleanup page and run the cleanup process. Review the output carefully before using it on production machines or shared computers.

## Project structure

- main.py: app entry point and Tkinter UI
- modules/cleanup.py: temporary-file cleanup logic
- modules/firewall.py: firewall rule and connection management
- modules/diagnostics.py: system and hardware information collection
- modules/hardware_services.py: integration with hardware libraries
- tests/: automated regression tests for the main features

## Troubleshooting

### The app does not show hardware details

Try these steps:

- confirm that the required libraries were installed;
- verify that the LibreHardwareMonitor files are present;
- run the app again after restarting the terminal.

### Firewall actions fail

If firewall actions fail, make sure:

- you are using an elevated terminal or running the app as administrator;
- Windows firewall services are available;
- the firewall rules you are editing are valid for the current profile.

### Cleanup does nothing or shows many blocked operations

Some folders may be protected by the operating system or by corporate policies. In that case, the cleanup step can skip them silently.

## Testing

Run the test suite with:

```bash
pytest -q
```

## Roadmap

This project continues to evolve with improvements in:

- better dashboard visualizations;
- more advanced firewall management;
- better rule history and reporting;
- stronger error handling and stability.

## License

This project is intended for personal and technical use. Please review the repository settings and any local licensing notes before redistributing it.
