import argparse
import os
import sys

from PIL import Image

acceptable_file_types = ['png', 'jpg', 'jpeg']


def get_texture_cache(datadir):
    directories = os.listdir(datadir)
    texture_cache = {}
    for d in directories:
        try:
            files = os.listdir(datadir + d)
            for f in files:
                try:
                    end = f[f.index('.') + 1:]
                except ValueError:
                    continue
                if not end in acceptable_file_types:
                    continue
                filename = f[:f.index('.')]
                print('found texture %s' % d + "/" + filename)
                img = Image.open(datadir + d + "/" + f, mode='r')
                texture_cache[d + "/" + filename] = img.size
                img.close()
        except NotADirectoryError:
            continue
    return texture_cache


def write_cache(datadir, cache):
    cache_file = open(datadir + "texturecache.txt", mode="wt")
    for name, p in cache.items():
        cache_file.write("%s %s %s\n" % (name, str(p[0]), str(p[1])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Texture cache tool")
    parser.add_argument("--data-dir", dest="datadir", required=True, type=str)
    args = parser.parse_args(sys.argv[1:])
    if str.endswith(args.datadir, "/") or str.endswith(args.datadir, "\\"):
        datadir = args.datadir + "textures/"
    else:
        datadir = args.datadir + "/textures/"
    write_cache(datadir, get_texture_cache(datadir))
