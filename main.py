from etn.database import DatabaseManager


if __name__ == "__main__":
    with DatabaseManager() as f:
        print(f"Testing: {f=}")
