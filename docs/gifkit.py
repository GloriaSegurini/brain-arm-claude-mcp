"""Tiny helpers for the demo GIFs: draw in 1x coordinates, render at SCALE x for sharp text,
and save without dithering (dithering is what makes GIF text look grainy)."""
from PIL import Image, ImageDraw, ImageFont

SCALE = 2


class Font:
    """A font whose measurements are in 1x units while it renders at SCALE x."""
    def __init__(self, path, size):
        self.real = ImageFont.truetype(path, int(size * SCALE))

    def getlength(self, text):
        return self.real.getlength(text) / SCALE


def _s(v):
    return v * SCALE


def _pts(xy):
    if isinstance(xy[0], (tuple, list)):
        return [(_s(x), _s(y)) for x, y in xy]
    return [_s(v) for v in xy]


class Draw:
    """ImageDraw wrapper taking 1x coordinates."""
    def __init__(self, img):
        self.d = ImageDraw.Draw(img)

    def text(self, xy, text, font, fill, anchor=None, stroke_width=0, stroke_fill=None):
        self.d.text((_s(xy[0]), _s(xy[1])), text, font=font.real, fill=fill, anchor=anchor,
                    stroke_width=int(stroke_width * SCALE), stroke_fill=stroke_fill)

    def line(self, xy, fill, width=1):
        self.d.line(_pts(xy), fill=fill, width=max(1, int(width * SCALE)))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.d.rectangle(_pts(xy), fill=fill, outline=outline, width=max(1, int(width * SCALE)))

    def rounded_rectangle(self, xy, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(_pts(xy), radius=_s(radius), fill=fill, outline=outline,
                                 width=max(1, int(width * SCALE)))


def new_image(w, h, color):
    return Image.new("RGB", (int(w * SCALE), int(h * SCALE)), color)


def save_gif(images, durations, out):
    frames = [im.convert("P", palette=Image.Palette.ADAPTIVE, colors=256, dither=Image.Dither.NONE)
              for im in images]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0,
                   optimize=False, disposal=1)
