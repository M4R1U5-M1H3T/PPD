import os
from fa_rg import BASE_DIR, RG, rg_to_fa

TESTS = {
    "rg_identifier.txt": (["fanPin", "readings", "i", "sensor_1", "A9b"],
                          ["", "2count", "_x", "fan-pin", "x y"]),
    "rg_number.txt": (["0", "9", "200", "1000"],
                      ["", "007", "01", "12a", "-5"]),
    "rg_string.txt": (['"Fan ON"', '"Average: "', '""', '"x = 5!"'],
                      ['"Fan ON', 'Fan', '"a#b"', '"a"b"']),
}


def main():
    failed = 0
    for file, (good, bad) in TESTS.items():
        rg = RG.from_file(os.path.join(BASE_DIR, file))
        assert rg.is_regular()
        fa = rg_to_fa(rg)
        for word in good + bad:
            if fa.accepts(word) != (word in good):
                failed += 1
                print(f"FAIL {file}: {word!r}")
        print(f"{file}: {len(good)} accepted, {len(bad)} rejected sequences checked")
    print("All tests passed." if failed == 0 else f"{failed} test(s) failed.")


if __name__ == "__main__":
    main()
