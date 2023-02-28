# Glasses

A TUI logviewer based on the Textual library. Trying to combine making a useful tool and getting to learn the textual library.

![glasses demo](./readme/glasses.gif)

## Installation

```
pipx install git+https://github.com/sander76/glasses.git#main --python=python3.10
```

to upgrade:

```
pipx upgrade glasses
```

This tool makes use of the `config` file located in your `.kube` folder (don't know whether this is also the location when running on mac or windows) to get the available namespaces. It also assumes you are logged into your openshift namespace.

## logging

Logs are kept under the `HOME/.config/glasses/log` folder.
To trace them during development:

```
tail -f glasses.log
```

## todo:

A lot of things. This needs some serious refactoring still. PR's are welcome !
