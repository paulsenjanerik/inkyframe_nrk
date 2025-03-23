from urllib import urequest
import gc
import qrcode
import time

# URL for NRK toppsaker
URL = "https://www.nrk.no/toppsaker.rss"

# Tid mellom hver oppdatering i minutter
UPDATE_INTERVAL = 15

# Tid mellom hvert nytt forsøk ved nettverksfeil (i sekunder)
RETRY_INTERVAL = 30

graphics = None
WIDTH = None
HEIGHT = None
code = qrcode.QRCode()


def read_until(stream, find):
    result = b""
    while len(c := stream.read(1)) > 0:
        if c == find:
            return result
        result += c


def discard_until(stream, find):
    _ = read_until(stream, find)


def parse_xml_stream(s, accept_tags, group_by, max_items=3):
    tag = []
    text = b""
    count = 0
    current = {}

    while True:
        char = s.read(1)
        if len(char) == 0:
            break

        if char == b"<":
            next_char = s.read(1)

            if next_char == b"?":
                discard_until(s, b">")
                continue

            elif next_char == b"!":
                s.read(1)
                discard_until(s, b"[")
                text = read_until(s, b"]")
                discard_until(s, b">")
                gc.collect()

            elif next_char == b"/":
                current_tag = read_until(s, b">")
                top_tag = tag[-1]

                if top_tag in accept_tags:
                    current[top_tag.decode("utf-8")] = text.decode("utf-8")

                elif top_tag == group_by:
                    yield current
                    current = {}
                    count += 1
                    if count == max_items:
                        return
                tag.pop()
                text = b""
                gc.collect()
                continue

            else:
                current_tag = read_until(s, b">")
                if not current_tag.endswith(b"/"):
                    tag += [next_char + current_tag.split(b" ")[0]]
                    text = b""

        else:
            text += char


def measure_qr_code(size, code):
    w, h = code.get_size()
    module_size = int(size / w)
    return module_size * w, module_size


def draw_qr_code(ox, oy, size, code):
    size, module_size = measure_qr_code(size, code)
    graphics.set_pen(1)
    graphics.rectangle(ox, oy, size, size)
    graphics.set_pen(0)
    for x in range(size):
        for y in range(size):
            if code.get_module(x, y):
                graphics.rectangle(ox + x * module_size, oy + y * module_size, module_size, module_size)


# Funksjon som henter data fra RSS-feeden fra NRK
def get_rss():
    while True:
        try:
            stream = urequest.urlopen(URL)
            output = list(parse_xml_stream(stream, [b"title", b"description", b"link", b"pubDate"], b"item"))
            return output

        except OSError as e:
            print(f"Nettverksfeil: {e}. Prøver på nytt om {RETRY_INTERVAL} sekunder...")
            time.sleep(RETRY_INTERVAL)


feed = None


def update():
    global feed
    feed = get_rss()


def draw():
    global feed
    graphics.set_font("bitmap8")

    graphics.set_pen(1)
    graphics.clear()
    graphics.set_pen(0)

    if len(feed) > 0:
        # Sett lik skriftstørrelse for begge overskriftene
        title_size = 3 if graphics.measure_text(feed[0]["title"]) < WIDTH - 130 else 2

        # Første nyhet (øverst) - QR-kode til høyre
        graphics.set_pen(4)
        graphics.text(feed[0]["title"], 10, 10, WIDTH - 130, title_size)
        graphics.set_pen(3)
        graphics.text(feed[0]["description"], 10, 70, WIDTH - 130, 2)

        code.set_text(feed[0]["link"])
        draw_qr_code(WIDTH - 110, 10, 100, code)  # QR-kode øverst til høyre

        graphics.line(10, 170, WIDTH - 10, 170)  # Linje mellom nyhetene

        # Andre nyhet (nederst) - QR-kode til venstre
        graphics.set_pen(4)
        graphics.text(feed[1]["title"], 130, 190, WIDTH - 140, title_size)
        graphics.set_pen(3)
        graphics.text(feed[1]["description"], 130, 250, WIDTH - 140, 2)

        code.set_text(feed[1]["link"])
        draw_qr_code(10, 190, 100, code)  # QR-kode nede til venstre

    else:
        graphics.set_pen(4)
        graphics.rectangle(0, (HEIGHT // 2) - 20, WIDTH, 40)
        graphics.set_pen(1)
        graphics.text("Kan ikke hente nyheter!", 5, (HEIGHT // 2) - 15, WIDTH, 2)
        graphics.text("Sjekk nettverksinnstillingene.", 5, (HEIGHT // 2) + 2, WIDTH, 2)

    graphics.update()
