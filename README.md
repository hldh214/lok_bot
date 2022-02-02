# lok_bot

Yet another League of Kingdoms farming bot

# Usage

```shell
python3 -m lokbot
```

## Docker

```shell
# build yourself
docker build -t lok_bot_local --build-arg PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple .
docker run lok_bot_local YOUR_X_ACCESS_TOKEN

# or use official docker image
docker run ghcr.io/hldh214/lok_bot YOUR_X_ACCESS_TOKEN
```

# X_ACCESS_TOKEN

`x-access-token` in request header

# References

https://github.com/miguelgrinberg/python-socketio/blob/v4.6.1/docs/client.rst
https://github.com/bambusbjoerni/bambusbjoerni.github.io
