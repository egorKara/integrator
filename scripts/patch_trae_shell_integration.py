import datetime
import hashlib
import pathlib
import shutil


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def main() -> None:
    target = pathlib.Path(
        r"C:\Users\egork\AppData\Local\Programs\Trae\resources\app\out\vs\workbench\workbench.desktop.main.js"
    )
    data = target.read_bytes()
    before_hash = sha256_bytes(data)

    needle = b"if(!e?.force&&await this.$c(e))return{commandDetection:r,invalidBuffer:n,success:!0};"
    repl = b"if(await this.$c(e))return{commandDetection:r,invalidBuffer:n,success:!0};"

    count = data.count(needle)
    if count != 1:
        raise SystemExit(f"Unexpected match count for needle: {count}")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak_{ts}")
    shutil.copyfile(target, backup)

    patched = data.replace(needle, repl)
    after_hash = sha256_bytes(patched)
    target.write_bytes(patched)

    print("OK")
    print(f"target={target}")
    print(f"backup={backup}")
    print(f"sha256_before={before_hash}")
    print(f"sha256_after={after_hash}")


if __name__ == "__main__":
    main()
