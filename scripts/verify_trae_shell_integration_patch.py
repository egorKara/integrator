import pathlib


def main() -> None:
    target = pathlib.Path(
        r"C:\Users\egork\AppData\Local\Programs\Trae\resources\app\out\vs\workbench\workbench.desktop.main.js"
    )
    data = target.read_bytes()
    needle = b"if(!e?.force&&await this.$c(e))return{commandDetection:r,invalidBuffer:n,success:!0};"
    repl = b"if(await this.$c(e))return{commandDetection:r,invalidBuffer:n,success:!0};"
    print(f"needle_count={data.count(needle)}")
    print(f"repl_count={data.count(repl)}")


if __name__ == "__main__":
    main()
