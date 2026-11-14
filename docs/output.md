verify 对照 fixtures/expected/ingest.json 比较 payload 文件名与 sha256，以及 quarantine 中必须出现 broken.bin 的 checksum_mismatch 和越界路径的 path_escape。photo.bin 必须来自缓存并入库。
