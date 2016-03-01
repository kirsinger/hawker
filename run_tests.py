import glob
import os

def main():
    tests = glob.iglob("./tests/test_*.py")
    for test in tests:
        test_name = os.path.split(
            os.path.splitext(
                test
            )[0]
        )[1]
        os.system("python -m tests.{}".format(test_name))

if __name__ == "__main__":
    main()
