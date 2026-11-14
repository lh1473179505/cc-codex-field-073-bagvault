# bagvault

库房丢过来的是 BagIt 包。按清单核对载荷，fetch.txt 里的远程文件只能用本地缓存补齐，路径越界或校验失败的成员进隔离区。

```
python -m bagvault ingest --bag fixtures/bags/shipment --cache fixtures/fetch-cache --out <out>
python -m bagvault verify --out <out> --expect fixtures/expected/ingest.json
```
