# Build Guide

## For Linux

```bash
./build.sh --linux
```

## For Windows

```bash
./build.sh --windows
```

## For Both Linux and Windows

```bash
./build.sh --all
```

# NVD DB

[Download](https://drive.google.com/file/d/1v5LEhRUGxo6irjnzZU4_pxbfF7111-Jh/view?usp=sharing)


## Service installation Guide

## Install service

* Install: (Creates directory, service file, and installs binary)


```bash 
  sudo ./manager.sh install
```

## Update service 

* Update: (Only replaces binary and restarts service — keeps config intact)

```bash
  sudo ./manager.sh update
```

## Status Checking

* Status: (Checks if running and shows recent logs)

```bash 
  sudo ./manager.sh status
```

## Uninstall service

* Uninstall: (Removes everything)

```bash
  sudo ./manager.sh uninstall
```

> Note: If you have your compiled file in your current folder (e.g., named dist/linux_agent), you run:

```bash
  sudo ./manager.sh install-local dist/linux_agent
```

## Releases
  [0.0.1](./docs/releases/release-v-0.0.1.md)