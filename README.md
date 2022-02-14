# Disclaimer

```c
#include <std_disclaimer.h>
/*
 *
 * We are not responsible for banned account or any other punishment by this game's GM. 
 * Please do some research if you have any concerns about features included in this repo
 * before using it! YOU are choosing to use these scripts, and if
 * you point the finger at us for messing up your account, we will laugh at you.
 *
 */
```

# lok_bot

[![GitHub issues](https://img.shields.io/github/issues/hldh214/lok_bot)](https://github.com/hldh214/lok_bot/issues)
[![GitHub forks](https://img.shields.io/github/forks/hldh214/lok_bot)](https://github.com/hldh214/lok_bot/network)
[![GitHub stars](https://img.shields.io/github/stars/hldh214/lok_bot)](https://github.com/hldh214/lok_bot/stargazers)
[![GitHub license](https://img.shields.io/github/license/hldh214/lok_bot)](https://github.com/hldh214/lok_bot/blob/master/LICENSE.md)

Yet another League of Kingdoms farming bot

# Usage

## Run with local Python interpreter

### Prerequisites

- [Python3.10](https://www.python.org/downloads/)
- [Pipenv](https://pipenv.pypa.io/en/latest/)

### Clone or download the repo

```shell
git clone https://github.com/hldh214/lok_bot.git
# or click "Download Zip" button
```

### Install requirements

```shell
cd lok_bot
pipenv sync
```

### Run

```shell
python3 -m lokbot YOUR_X_ACCESS_TOKEN
```

## Run with Docker

### Build image yourself

```shell
docker build -t lok_bot_local --build-arg PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple .
docker run -e TOKEN=YOUR_X_ACCESS_TOKEN lok_bot_local
```

### Or use prebuilt image

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/hldh214/lok_bot/Docker%20Image%20CI.svg)](https://github.com/hldh214/lok_bot/pkgs/container/lok_bot)

```shell
docker run -e TOKEN=YOUR_X_ACCESS_TOKEN ghcr.io/hldh214/lok_bot
```

# X_ACCESS_TOKEN

There are currently no plans to support login functionality. So we need this `X_ACCESS_TOKEN` trick to made it works.

![x-access-token.webp](docs/images/x-access-token.webp)

You need to log in on the web, then press F12 to open [DevTools](https://developer.chrome.com/docs/devtools/open/). Then
click `Network` tab(1)(2), scroll down to the latest request and click it(3). On the right side(4) scroll down to the
bottom, and you can see `x-access-token` field(5). Copy that value and pass it as `X_ACCESS_TOKEN` mentioned above.

# Buy Me a Coffee

ETH/Matic: 0x27C7993CC3349DDE839B4F921733CFc523385864

# References

https://github.com/miguelgrinberg/python-socketio/blob/v4.6.1/docs/client.rst
https://github.com/bambusbjoerni/bambusbjoerni.github.io
