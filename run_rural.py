
# run_rural.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
from cli_rural.__main__ import main

if __name__ == "__main__":
    main()
