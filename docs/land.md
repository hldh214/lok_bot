# Land

```js
let zone_id = 64 * parseInt(yaxis / 32) + parseInt(xaxis / 32)
```

## world

```
world: 1 * 1 (inner: 2048 * 2048)
    zone: 64 * 64 (inner: 32 * 32) -> a world have 4096 zones
        land: 256 * 256 (inner: 8 * 8) -> a zone have 16 lands
```

## land

```
land: 256*256 (inner: 8 * 8)
id start from 100000

here is a zone's all lands(land_id) (zone_id=1):
100768 ...    ...    100771
100512 ...    ...    ...
100256 ...    ...    ...
100000 100001 100002 100003
```

## coordinate

```
coordinate:
    x: 0 ~ 2047
    y: 0 ~ 2047
start from left-bottom corner
```

```
devrank 256 * 256 == 65536 <- so it means land's scale

we need to find most valuable land
then dive into these lands to find some mines
```
