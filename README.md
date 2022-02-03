# lok_bot

Yet another League of Kingdoms farming bot

# Usage

```shell
python3 -m lokbot YOUR_X_ACCESS_TOKEN
```

## Docker

```shell
# build yourself
docker build -t lok_bot_local --build-arg PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple .
docker run -e TOKEN=YOUR_X_ACCESS_TOKEN lok_bot_local

# or use official docker image
docker run -e TOKEN=YOUR_X_ACCESS_TOKEN ghcr.io/hldh214/lok_bot
```

# X_ACCESS_TOKEN

`x-access-token` in request header

# References

https://github.com/miguelgrinberg/python-socketio/blob/v4.6.1/docs/client.rst
https://github.com/bambusbjoerni/bambusbjoerni.github.io
