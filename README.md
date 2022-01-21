# lok_bot

Yet another League of Kingdoms farming bot

# Usage

```shell
python3 lok_bot.py YOUR_X_ACCESS_TOKEN
```

## Docker

```shell
docker build -t lok_bot_local --build-arg PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple .
docker run lok_bot_local YOUR_X_ACCESS_TOKEN
```

# X_ACCESS_TOKEN

`x-access-token` in request header
