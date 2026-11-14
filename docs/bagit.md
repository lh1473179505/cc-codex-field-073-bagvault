# BagIt 入库

包根目录里有 `bagit.txt`、`bag-info.txt`、`manifest-sha256.txt`、`tagmanifest-sha256.txt` 和可选的 `fetch.txt`。版本按 1.0 处理。不要访问外网，不要用 Docker。

## 校验

对 `manifest-sha256.txt` 中的每个载荷路径计算 sha256（十六进制小写），对不上的进入 `--out/quarantine.jsonl`（`path,reason=checksum_mismatch`），不要写到 payload 里。

`fetch.txt` 每行是：`URL 字节长度 data/相对路径`。这些文件不在包里，只能从 `--cache` 目录补齐。缓存映射见 `fixtures/fetch-cache/index.json`（键是 URL，值是缓存文件名）。找不到缓存或企图请求网络时，该条目 `reason=missing_cache`，不得发 HTTP。

## 路径

清单里的路径必须落在 `data/` 之下。含 `..` 或绝对路径的成员一律 `reason=path_escape`，不得写出到 `--out` 之外，也不得写到输出根目录的上一级。

tagmanifest 用于核对 tag 文件本身；若 tagmanifest 与 bagit.txt / manifest-sha256.txt / fetch.txt 的当前内容不一致，把该 tag 文件记入 quarantine（`reason=tag_mismatch`），载荷仍按 manifest 继续处理。本夹具的 tagmanifest 是自洽的。

输出：`--out/payload/` 下保留相对 `data/` 的安全文件；`--out/report.json` 含 `payload_count`、`quarantine_count`。
