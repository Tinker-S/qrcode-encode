from qrcode import constants, exceptions, util
from PIL import Image, ImageDraw
import math

def make(data=None, **kwargs):
    qr = QRCode(**kwargs)
    qr.add_data(data)
    return qr.make_image()

class QRCode:
    def __init__(self, version=None,
                 error_correction=constants.ERROR_CORRECT_H,
                 size=300,border=2,is_water=False,is_round=False,radius=0,fore_color='black',back_color='white',back_img=None,effect=None):
        self.version = version and int(version)
        self.error_correction = int(error_correction)
        self.size=int(size)
        # Spec says border should be at least four boxes wide, but allow for
        # any (e.g. for producing printable QR codes).
        self.border = int(border)
        self.is_water = is_water
        self.is_round = is_round
        self.radius = radius
        self.fore_color = fore_color
        self.back_color = back_color
        if back_img:
            self.back_img = Image.open(back_img)
        else:
            self.back_img = None
        self.effect=effect

        self.clear()

    def clear(self):
        """
        Reset the internal data.
        """
        self.modules = None
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def add_data(self, data, optimize=20):
        """
        Add data to this QR Code.

        :param optimize: Data will be split into multiple chunks to optimize
            the QR size by finding to more compressed modes of at least this
            length. Set to ``0`` to avoid optimizing at all.
        """
        if isinstance(data, util.QRData):
            self.data_list.append(data)
        else:
            if optimize:
                self.data_list.extend(util.optimal_data_chunks(data))
            else:
                self.data_list.append(util.QRData(data))
        self.data_cache = None

    def make(self, fit=True):
        """
        Compile the data into a QR Code array.

        :param fit: If ``True`` (or if a size has not been provided), find the
            best fit for the data to avoid data overflow errors.
        """
        if fit or not self.version:
            self.best_fit(start=self.version)
        self.makeImpl(False, self.best_mask_pattern())

    def makeImpl(self, test, mask_pattern):
        self.modules_count = self.version * 4 + 17
        self.modules = [None] * self.modules_count

        qr_size = self.modules_count + (self.border << 1)
        self.size = max(qr_size, self.size)
        self.box_size = self.size / qr_size
        self.padding = (self.size - self.box_size * self.modules_count) / 2

        for row in range(self.modules_count):
            self.modules[row] = [None] * self.modules_count
            for col in range(self.modules_count):
                self.modules[row][col] = None   # (col + row) % 3

        self.setup_position_probe_pattern(0, 0)
        self.setup_position_probe_pattern(self.modules_count - 7, 0)
        self.setup_position_probe_pattern(0, self.modules_count - 7)
        self.sutup_position_adjust_pattern()
        self.setup_timing_pattern()
        self.setup_type_info(test, mask_pattern)

        if self.version >= 7:
            self.setup_type_number(test)

        if self.data_cache is None:
            self.data_cache = util.create_data(
                self.version, self.error_correction, self.data_list)
        self.map_data(self.data_cache, mask_pattern)

    def setup_position_probe_pattern(self, row, col):
        for r in range(-1, 8):

            if row + r <= -1 or self.modules_count <= row + r:
                continue

            for c in range(-1, 8):

                if col + c <= -1 or self.modules_count <= col + c:
                    continue

                if (0 <= r and r <= 6 and (c == 0 or c == 6)
                        or (0 <= c and c <= 6 and (r == 0 or r == 6))
                        or (2 <= r and r <= 4 and 2 <= c and c <= 4)):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False

    def best_fit(self, start=None):
        """
        Find the minimum size required to fit in the data.
        """
        size = start or 1
        while True:
            try:
                self.data_cache = util.create_data(
                    size, self.error_correction, self.data_list)
            except exceptions.DataOverflowError:
                size += 1
            else:
                self.version = size
                return size

    def best_mask_pattern(self):
        """
        Find the most efficient mask pattern.
        """
        min_lost_point = 0
        pattern = 0

        for i in range(8):
            self.makeImpl(True, i)

            lost_point = util.lost_point(self.modules)

            if i == 0 or min_lost_point > lost_point:
                min_lost_point = lost_point
                pattern = i

        return pattern

    def print_tty(self, out=None):
        pass

    def isset(self, row, column):
        if row < 0 or row > self.modules_count - 1 or column < 0 or column > self.modules_count - 1:
            return False
        return self.modules[row][column]

    def make_image(self, **kwargs):
        """
        Make an image from the QR Code data.

        If the data has not been compiled yet, make it first.
        """
        if self.data_cache is None:
            self.make()

        self.img = Image.new("RGBA", (self.size, self.size), self.back_color)
        self.idr = ImageDraw.Draw(self.img)

        if self.effect == 'angry_bird':
            return self.make_angry_bird()

        for r in range(self.modules_count):
            for c in range(self.modules_count):
                if self.effect == 'square':
                    if self.modules[r][c] == 1:
                        index = [0, 0]
                        for i in xrange(self.box_size / 2 + 1):
                            h = 1 if (i == 0 or (self.box_size % 2 == 0 and i == self.box_size / 2)) else 2
                            for j in xrange(self.box_size / 2 + 1):
                                w = 1 if (j == 0 or (self.box_size % 2 == 0 and j == self.box_size / 2)) else 2

                                box = (self.padding + c * self.box_size + index[0], self.padding + r * self.box_size + index[1], self.padding + c * self.box_size + index[0] + w - 1, self.padding + r * self.box_size + index[1] + h - 1)
                                self.idr.rectangle(box, fill=(0, 0, 0, 255) if (j % 2 == i % 2) else (0, 0, 0, 0))
                                index[0] += w
                            index[0] = 0
                            index[1] += h
                    else:
                        index = [0, 0]
                        for i in xrange(self.box_size / 2 + 1):
                            h = 1 if (i == 0 or (self.box_size % 2 == 0 and i == self.box_size / 2)) else 2
                            for j in xrange(self.box_size / 2 + 1):
                                w = 1 if (j == 0 or (self.box_size % 2 == 0 and j == self.box_size / 2)) else 2

                                box = (self.padding + c * self.box_size + index[0], self.padding + r * self.box_size + index[1], self.padding + c * self.box_size + index[0] + w - 1, self.padding + r * self.box_size + index[1] + h - 1)
                                self.idr.rectangle(box, fill=(255, 255, 255, 255) if (j % 2 == i % 2) else (0, 0, 0, 0))
                                index[0] += w
                            index[0] = 0
                            index[1] += h
                else:
                    if self.modules[r][c]:
                        left_top = False
                        left_bottom = False
                        right_top = False
                        right_bottom = False

                        if self.is_water:
                            if (not self.isset(r, c - 1)) and (not self.isset(r - 1, c - 1)) and (not self.isset(r - 1, c)):
                                left_top = True
                            if (not self.isset(r - 1, c)) and (not self.isset(r - 1, c + 1)) and (not self.isset(r, c + 1)):
                                right_top = True
                            if (not self.isset(r, c + 1)) and (not self.isset(r + 1, c + 1)) and (not self.isset(r + 1, c)):
                                right_bottom = True
                            if (not self.isset(r, c - 1)) and (not self.isset(r + 1, c - 1)) and (not self.isset(r + 1, c)):
                                left_bottom = True
                        elif self.is_round:
                            left_top = True
                            left_bottom = True
                            right_top = True
                            right_bottom = True
                        util.draw_round_rectangle(self.idr, self.padding + c * self.box_size, self.padding + r * self.box_size, self.box_size, self.radius, left_top, right_top, right_bottom, left_bottom, self.fore_color, self.back_color)
                    else:
                        if self.is_water:
                            left_top = False
                            left_bottom = False
                            right_top = False
                            right_bottom = False

                            if self.isset(r, c - 1) and self.isset(r - 1, c):
                                left_top = True
                            if self.isset(r, c + 1) and self.isset(r - 1, c):
                                right_top = True
                            if self.isset(r, c + 1) and self.isset(r + 1, c):
                                right_bottom = True
                            if self.isset(r, c - 1) and self.isset(r + 1, c):
                                left_bottom = True

                            util.draw_round_rectangle(self.idr, self.padding + c * self.box_size, self.padding + r * self.box_size, self.box_size, self.radius, left_top, right_top, right_bottom, left_bottom, self.back_color, self.fore_color)
        return self.compose_image(self.img, self.back_img)

    def setup_timing_pattern(self):
        for r in range(8, self.modules_count - 8):
            if self.modules[r][6] is not None:
                continue
            self.modules[r][6] = (r % 2 == 0)

        for c in range(8, self.modules_count - 8):
            if self.modules[6][c] is not None:
                continue
            self.modules[6][c] = (c % 2 == 0)

    def sutup_position_adjust_pattern(self):
        pos = util.pattern_position(self.version)

        for i in range(len(pos)):

            for j in range(len(pos)):

                row = pos[i]
                col = pos[j]

                if self.modules[row][col] is not None:
                    continue

                for r in range(-2, 3):

                    for c in range(-2, 3):

                        if (r == -2 or r == 2 or c == -2 or c == 2 or
                                (r == 0 and c == 0)):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def setup_type_number(self, test):
        bits = util.BCH_type_number(self.version)

        for i in range(18):
            mod = (not test and ((bits >> i) & 1) == 1)
            self.modules[i // 3][i % 3 + self.modules_count - 8 - 3] = mod

        for i in range(18):
            mod = (not test and ((bits >> i) & 1) == 1)
            self.modules[i % 3 + self.modules_count - 8 - 3][i // 3] = mod

    def setup_type_info(self, test, mask_pattern):
        data = (self.error_correction << 3) | mask_pattern
        bits = util.BCH_type_info(data)

        # vertical
        for i in range(15):

            mod = (not test and ((bits >> i) & 1) == 1)

            if i < 6:
                self.modules[i][8] = mod
            elif i < 8:
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.modules_count - 15 + i][8] = mod

        # horizontal
        for i in range(15):

            mod = (not test and ((bits >> i) & 1) == 1)

            if i < 8:
                self.modules[8][self.modules_count - i - 1] = mod
            elif i < 9:
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod

        # fixed module
        self.modules[self.modules_count - 8][8] = (not test)

    def map_data(self, data, mask_pattern):
        inc = -1
        row = self.modules_count - 1
        bitIndex = 7
        byteIndex = 0

        mask_func = util.mask_func(mask_pattern)

        for col in range(self.modules_count - 1, 0, -2):

            if col <= 6:
                col -= 1

            while True:

                for c in range(2):

                    if self.modules[row][col - c] is None:

                        dark = False

                        if byteIndex < len(data):
                            dark = (((data[byteIndex] >> bitIndex) & 1) == 1)

                        if mask_func(row, col - c):
                            dark = not dark

                        self.modules[row][col - c] = dark
                        bitIndex -= 1

                        if bitIndex == -1:
                            byteIndex += 1
                            bitIndex = 7

                row += inc

                if row < 0 or self.modules_count <= row:
                    row -= inc
                    inc = -inc
                    break

    def get_matrix(self):
        """
        Return the QR Code as a multidimensonal array, including the border.

        To return the array without a border, set ``self.border`` to 0 first.
        """
        if self.data_cache is None:
            self.make()

        if not self.border:
            return self.modules

        width = len(self.modules) + self.border*2
        code = [[False]*width] * self.border
        x_border = [False]*self.border
        for module in self.modules:
            code.append(x_border + module + x_border)
        code += [[False]*width] * self.border

        return code

    def save(self, stream):
        self.img.save(stream)

    def compose_image(self, top, bottom):
        if self.effect == 'square':
            return self.square_compose(top, bottom);
        else:
            return self.simple_compose(top, bottom);

    def square_compose(self, top, bottom):
        if bottom == None:
            return top

        resize_width = self.size - (self.padding << 1)
        bottom = bottom.resize((resize_width, resize_width))
        bottom = bottom.convert('RGBA')

        l = [None, None, None, None]
        for i in xrange(self.size):
            if i < self.padding or i > self.size - 1 - self.padding:
                continue
            for j in xrange(self.size):
                if j < self.padding or j > self.size - 1 - self.padding:
                    continue
                top_color = top.getpixel((i, j))
                bottom_color = bottom.getpixel((i - self.padding, j - self.padding))

                if top_color[3] == 0:
                    l = bottom_color
                else:
                    l = top_color
                top.putpixel((i, j), tuple(l))
        return top

    def simple_compose(self, top, bottom):
        if bottom == None:
            return top

        resize_width = self.size - (self.padding << 1)
        bottom = bottom.resize((resize_width, resize_width))
        bottom = bottom.convert('RGBA')
        #bottom = self.mosaic_image(bottom);
        bottom.save('test.jpg')

        bottom_coefficient = 0.8
        coefficient = 0.4

        l = [None, None, None, None]
        for i in xrange(self.size):
            if i < self.padding or i > self.size - 1 - self.padding:
                continue
            for j in xrange(self.size):
                if j < self.padding or j > self.size - 1 - self.padding:
                    continue
                top_color = top.getpixel((i, j))
                #print "i = ", i, "j = ", j
                #print "ii = ", i - resize_padding, "jj = ", j - resize_padding
                bottom_color = bottom.getpixel((i - self.padding, j - self.padding))
                #l[0] = int(math.floor(top_color[0] * 0.5 + bottom_color[0] * 0.5))
                #l[1] = int(math.floor(top_color[1] * 0.5 + bottom_color[1] * 0.5))
                #l[2] = int(math.floor(top_color[2] * 0.5 + bottom_color[2] * 0.5))
                #l[3] = int(math.floor(top_color[3] * 0.5 + bottom_color[3] * 0.5))
                if top_color[0] == 0:
                    l[0] = int(bottom_color[0] * bottom_coefficient)
                    l[1] = int(bottom_color[1] * bottom_coefficient)
                    l[2] = int(bottom_color[2] * bottom_coefficient)
                    l[3] = int(bottom_color[3] * bottom_coefficient)
                else:
                    l[0] = int(math.floor(top_color[0] * (1 - coefficient) + bottom_color[0] * coefficient))
                    l[1] = int(math.floor(top_color[1] * (1 - coefficient) + bottom_color[1] * coefficient))
                    l[2] = int(math.floor(top_color[2] * (1 - coefficient) + bottom_color[2] * coefficient))
                    l[3] = int(math.floor(top_color[3] * (1 - coefficient) + bottom_color[3] * coefficient))
                top.putpixel((i, j), tuple(l))
        return top

    def mosaic_image(self, image):
        radius = self.box_size
        result = Image.new(image.mode, image.size)
        width, height = image.size

        for i in xrange(self.modules_count):
            for j in xrange(self.modules_count):
                color = image.getpixel((i * radius, j * radius))
                for m in xrange(radius):
                    for n in xrange(radius):
                        result.putpixel((i * radius + m, j * radius + n), color)
        return result

    def is_finder_patter(self, row, col):
        if row >= 0 and row <= 6 and col >= 0 and col <= 6:
            return True
        if col >= self.modules_count - 7 and col <= self.modules_count - 1 and row >= 0 and row <= 6:
            return True
        if row >= self.modules_count - 7 and row <= self.modules_count - 1 and col >= 0 and col <= 6:
            return True
        return False

    def open_image_resource(self, path):
        img = Image.open(path)
        img = img.convert('RGBA')
        return img

    def make_angry_bird(self):
        bird = self.open_image_resource('res/bird.jpg')
        bar1 = self.open_image_resource('res/bar1.jpg')
        hbar2 = self.open_image_resource('res/hbar2.jpg')
        vbar2 = self.open_image_resource('res/vbar2.jpg')
        finder = self.open_image_resource('res/finder.jpg')
        bird = bird.resize([2 * self.box_size, 2 * self.box_size])
        bar1 = bar1.resize([self.box_size, self.box_size])
        hbar2 = hbar2.resize([2 * self.box_size, self.box_size])
        vbar2 = vbar2.resize([self.box_size, 2 * self.box_size])
        finder = finder.resize([7 * self.box_size, 7 * self.box_size])

        self.img.paste(finder, (self.padding, self.padding))
        self.img.paste(finder, ((self.modules_count - 7) * self.box_size + self.padding, self.padding))
        self.img.paste(finder, (self.padding, (self.modules_count - 7) * self.box_size + self.padding))

        is_drawn = [[False for i in xrange(self.modules_count)] for j in xrange(self.modules_count)]

        for r in xrange(self.modules_count):
            for c in xrange(self.modules_count):
                if self.is_finder_patter(r, c):
                    continue

                if self.modules[c][r] == 1:
                    if is_drawn[c][r]:
                        continue

                    box = (self.padding + c * self.box_size, self.padding + r * self.box_size)
                    if self.isset(c + 1, r) and self.isset(c + 1, r + 1) and self.isset(c, r + 1) and not is_drawn[c + 1][r + 1] and not is_drawn[c + 1][r] and not is_drawn[c][r + 1]:
                        self.img.paste(bird, box)

                        is_drawn[c + 1][r] = True
                        is_drawn[c + 1][r + 1] = True
                        is_drawn[c][r + 1] = True
                    elif self.isset(c, r + 1) and not is_drawn[c][r + 1]:
                        self.img.paste(vbar2, box)
                        is_drawn[c][r + 1] = True
                    elif self.isset(c + 1, r) and not is_drawn[c + 1][r]:
                        self.img.paste(hbar2, box)
                        is_drawn[c + 1][r] = True
                    else:
                        self.img.paste(bar1, box)

                    is_drawn[c][r] = True

        return self.img
