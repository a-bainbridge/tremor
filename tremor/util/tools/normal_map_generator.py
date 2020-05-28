import math
import sys

import PIL.Image as PIL_Image
import numpy as np


def norm_vec3(vec):
    mag = max(np.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2]), 0.0001)
    return np.array([vec[0] / mag, vec[1] / mag, vec[2] / mag], dtype='float32')


def main(args):
    if '-h' in args or '--help' in args or 'help' in args:
        print("""
        usage: python normal_map_generator.py <INPUT> <OUTPUT> [options]
        INPUT    filename of input heightmap
        OUTPUT   filename for output normalmap
        
        options:
        -h; --help       display this menu
        -i <f>           f is a float where 0 < f <= 1, default 0.1
        --max-angle <a>  a is angle in degrees, 0 < a < 90, default 45
        """)
        return
    intensity = 10
    max_angle = np.pi / 2
    if '-i' in args:
        intensity = 1 / float(args[args.index('-i') + 1])
        print(f'set intesnity to {1 / intensity}')
    if '--max-angle' in args:
        max_angle = float(args[args.index('--max-angle') + 1])
        print(f'set max angle to {max_angle}')
        max_angle = max_angle / 180 * np.pi
    input_filename = args[1]
    output_filename = args[2]
    heightmap: PIL_Image.Image = PIL_Image.open(input_filename)
    if heightmap.mode != 'L':
        heightmap = heightmap.convert('L')
    normalmap: PIL_Image.Image = PIL_Image.new('RGB', heightmap.size)

    # z is up on a normal map
    sa = np.sin(max_angle)
    ca = np.cos(max_angle)
    up = np.array([0, 0, 1])
    tangent = np.array([sa, 0, ca])
    bitangent = np.array([0, sa, ca])
    resc = lambda v, lower, upper, nlower, nupper: (v - lower) / (upper - lower) * (nupper - nlower) + nlower

    epsilon = 1
    # excludes border
    for y in range(epsilon, heightmap.height - epsilon):
        for x in range(epsilon, heightmap.width - epsilon):
            xgrad = get_gradient(heightmap, (x, y), (epsilon, 0))
            ygrad = get_gradient(heightmap, (x, y), (0, epsilon))
            xgrad = resc(xgrad, -intensity, intensity, -1, 1)
            ygrad = resc(ygrad, -intensity, intensity, -1, 1)

            xvec = up * (1 - xgrad) + tangent * xgrad
            yvec = up * (1 - ygrad) + bitangent * ygrad
            col = (norm_vec3(xvec + yvec) + 1) / 2 * 255
            col = (int(col[0]), int(col[1]), int(col[2]))
            normalmap.putpixel((x, y), col)

    # finish borders by copying
    for y in range(1, heightmap.height - 1):  # | |
        normalmap.putpixel((0, y), normalmap.getpixel((1, y)))
        normalmap.putpixel((normalmap.width - 1, y), normalmap.getpixel((normalmap.width - 2, y)))
    for x in range(0, heightmap.width):  # bottom and top
        normalmap.putpixel((x, 0), normalmap.getpixel((x, 1)))
        normalmap.putpixel((x, normalmap.height - 1), normalmap.getpixel((x, normalmap.height - 2)))

    normalmap.save(output_filename)
    normalmap.show()


def get_gradient(img, xy, disp):
    first = img.getpixel((xy[0] + disp[0], xy[1] + disp[1]))
    other = img.getpixel((xy[0] - disp[0], xy[1] - disp[1]))
    slope = (first - other) / math.sqrt(disp[0] ** 2 + disp[1] ** 2)
    return slope


if __name__ == '__main__':
    main(sys.argv)
