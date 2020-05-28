import argparse
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dedicated", dest="dedicated", action='store_true')
    parser.add_argument("commands", type=str, nargs="+")
    args = parser.parse_args(sys.argv)
    if args.dedicated:
        from tremor import server_main

        server_main.main()
    else:
        from tremor import client_main

        client_main.main()
