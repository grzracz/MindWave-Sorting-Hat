import socket
import threading
import pygame
import random

from queue import Queue
from ctypes import pointer, POINTER, cast, c_int, c_float

TCP_IP = '127.0.0.1'
TCP_PORT = 13854
BUFFER_SIZE = 1024
INSTANCES_NUMBER = 4
WIDTH = 1920
HEIGHT = 1080


class LastInstances:
    def __init__(self, number_of_instances):
        self.instances = []
        for i1 in range(0, number_of_instances):
            self.instances.append(0)
        self.last = -1
        self.amount = number_of_instances
        self.average = 0
        self.total_average = 0
        self.total_amount = 0

    def add(self, value):
        self.total_amount += 1
        self.total_average += (value - self.total_average)/self.total_amount
        self.last = (self.last + 1) % self.amount
        self.instances[self.last] = value
        _sum = 0
        for i1 in range(0, self.amount):
            _sum += self.instances[i1]
        self.average = _sum / self.amount

    def get_last(self):
        if self.last == -1:
            return -1
        else:
            return self.instances[self.last]

    def reset(self):
        self.last = -1
        self.average = 0
        self.total_average = 0
        self.total_amount = 0
        for i1 in range(0, self.amount):
            self.instances[i1] = 0


class MindWaveClient:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((TCP_IP, TCP_PORT))
        self.buffer = Queue(5)
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def run(self):
        while not True:
            mindwave_data = self.s.recv(BUFFER_SIZE).hex().upper()
            if mindwave_data and not self.buffer.full():
                if len(mindwave_data) < 50:
                    print("Syncing...")
                else:
                    self.buffer.put(mindwave_data)
            elif mindwave_data:
                print("Buffer is full:", mindwave_data)

    def get(self):
        if not self.buffer.empty():
            return self.buffer.get()
        else:
            return None

    def empty(self):
        return self.buffer.empty()

    def reset(self):
        while not self.buffer.empty():
            self.buffer.get()


def get_next_byte(string, last_byte):
    if string[last_byte:last_byte + 2] is "":
        return "", 0
    else:
        return string[last_byte:last_byte+2], last_byte+2


def byte_to_float(string):
    string = str(int(string[0]) - 1) + string[1:]
    return convert(string)


def convert(_s):
    i1 = int(_s, 16)
    cp = pointer(c_int(i1))
    fp = cast(cp, POINTER(c_float))
    return fp.contents.value


class MindWaveParser:
    def __init__(self):
        self.MindWave = MindWaveClient()
        self.last_byte_number = 0
        self.parsed_string = ""
        self.waves = ["Delta", "Theta", "low Alpha", "high Alpha", "low Beta", "high Beta", "low Gamma", "high Gamma"]
        self.signal = LastInstances(INSTANCES_NUMBER)
        self.attention = LastInstances(INSTANCES_NUMBER)
        self.meditation = LastInstances(INSTANCES_NUMBER)
        self.waves_values = []
        self.last_signal = 200
        for i1 in range(0, 8):
            self.waves_values.append(LastInstances(INSTANCES_NUMBER))
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def run(self):
        while True:
            if not self.MindWave.empty():
                data = self.MindWave.get()
                while True:
                    current_byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                    if current_byte == "AA":  # Data starts being sent
                        current_byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                        self.parsed_string += "SYNCED: "
                    elif current_byte == "02":  # Signal value (0 - 200), where 0 - perfect, 200 - off head state
                        byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                        self.parsed_string += "Signal: " + str(int(byte, 16)) + "; "
                        self.signal.add(int(byte, 16))
                        self.last_signal = int(byte, 16)
                    elif current_byte == "04":  # Attention value (0 - 100)
                        byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                        self.parsed_string += "Attention: " + str(int(byte, 16)) + "; "
                        if self.last_signal == 0:
                            self.attention.add(int(byte, 16))
                    elif current_byte == "05":  # Meditation value (0 - 100)
                        byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                        self.parsed_string += "Meditation: " + str(int(byte, 16)) + "; "
                        if self.last_signal == 0:
                            self.meditation.add(int(byte, 16))
                    elif current_byte == "81":  # EEG values as represented in waves array
                        current_byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                        self.parsed_string += "EEG waves: "
                        for i1 in range(0, 8):
                            float_string = ""
                            for i2 in range(0, 4):
                                current_byte, self.last_byte_number = get_next_byte(data, self.last_byte_number)
                                float_string += current_byte
                            self.parsed_string += self.waves[i1] + ": " + str(byte_to_float(float_string)) + "; "
                            if not byte_to_float(float_string) < 0:
                                if self.last_signal == 0:
                                    self.waves_values[i1].add(byte_to_float(float_string))
                    elif current_byte != "":
                        print("Unknown byte:", current_byte)
                    if self.last_byte_number == 0:
                        print("")
                        print("Signal:", self.signal.average, "total:", self.signal.total_average)
                        print("Attention:", self.attention.average, "total:", self.attention.total_average)
                        print("Meditation:", self.meditation.average, "total:", self.meditation.total_average)
                        print("Waves:")
                        for i1 in range(0, 8):
                            print(self.waves[i1] + ":", self.waves_values[i1].average,
                                  "total:", self.waves_values[i1].total_average)
                        self.parsed_string = ""
                        break

    def reset(self):
        self.MindWave.reset()
        self.last_byte_number = 0
        self.parsed_string = ""
        self.signal.reset()
        self.attention.reset()
        self.meditation.reset()
        self.last_signal = 200
        for i1 in range(0, 8):
            self.waves_values[i1].reset()


class Colors:
    def __init__(self):
        self.black = (0, 0, 0)
        self.black5 = (5, 5, 5)
        self.white = (255, 255, 255)
        self.red = (255, 0, 0)
        self.blue = (0, 0, 255)
        self.lime = (0, 255, 0)
        self.gray = (20, 20, 20)
        self.yellow = (255, 255, 0)
        self.cyan = (0, 255, 255)
        self.green = (0, 128, 0)
        self.teal = (0, 128, 128)
        self.pink = (255, 192, 203)
        self.orange = (255, 165, 0)
        self.magenta = (255, 0, 255)
        self.cornsilk = (255, 248, 220)
        self.skyblue = (0, 191, 255)
        self.chocolate = (210, 105, 30)
        self.brown = (165, 42, 42)
        self.beige = (245, 245, 220)
        self.salmon = (240, 128, 114)
        self.lightgray = (211, 211, 211)
        self.lightgreen = (0, 255, 0)
        self.medgreen = (0, 192, 0)
        self.darkred = (128, 0, 0)
        self.medred = (192, 0, 0)


def clear_window(_window, _x, _y, _width, _height):
    pygame.draw.rect(window, c.black5, pygame.Rect(_x, _y, _width, _height))


def text_to_surface(_text, big):
    if big:
        _text_render = font_big.render(_text, True, c.black5)
    else:
        _text_render = font_medium.render(_text, True, c.black5)
    return _text_render


class SpeechOperator:
    def __init__(self, _parser):
        self.wave_baselines = [0.000085520879017, 0.000021897343866,        # baseline based on readings from 3 people
                               0.000005682946818, 0.000004351168889,
                               0.000003498963247, 0.000002834064985,
                               0.000002102321697, 0.000001087921237]

        self.houses = ["Gryffindor",
                       "Hufflepuff",
                       "Ravenclaw",
                       "Slytherin"]

        self.on_start = ["Where shall I put you? Let's see...",
                         "This is interesting.",
                         "Difficult, very difficult.",
                         "Are you afraid of what you will hear?",
                         "Don’t worry, child."]

        self.random = ["Ah, right then.",
                       "Hmm, okay...",
                       "I think I know what to do with you..."]

        self.house_quotes = []
        for i1 in range(0, 4):
            self.house_quotes.append([])
        self.house_quotes[0] = ["Plenty of courage...",
                                "Yes... very brave.",
                                "You have a lot of nerve!",
                                "GRYFFINDOR!"]

        self.house_quotes[1] = ["Patient and loyal...",
                                "Hard work will get you far.",
                                "Strong sense of justice...",
                                "HUFFLEPUFF!"]

        self.house_quotes[2] = ["Not a bad mind.",
                                "There's talent! Interesting...",
                                "Quite smart...",
                                "RAVENCLAW!"]

        self.house_quotes[3] = ["A nice thirst to prove yourself.",
                                "Quite ambitious, yes...",
                                "Great sense of self-preservation...",
                                "SLITHERIN!"]

        self.seconds = 4
        self.used_quotes = []
        self.parser = _parser
        self.house_points = []  # Gryffindor, Hufflepuff, Ravenclaw, Slytherin
        for i1 in range(0, 4):
            self.house_points.append(0)

    def update(self):
        _text = None
        _frames = 0
        _big_text = False
        if self.parser.waves_values[0].total_amount >= 11:
            self.house_points[0] += ((2 * self.parser.wave_values[6].average) /
                                     (self.parser.wave_values[6].total_average + self.wave_baselines[6])) + \
                                    ((2 * self.parser.wave_values[7].average) /
                                     (self.parser.wave_values[7].total_average + self.wave_baselines[7]))
            self.house_points[1] += ((2 * self.parser.wave_values[0].average) /
                                     (self.parser.wave_values[0].total_average + self.wave_baselines[0])) + \
                                    ((2 * self.parser.wave_values[4].average) /
                                     (self.parser.wave_values[4].total_average + self.wave_baselines[4]))
            self.house_points[2] += ((2 * self.parser.wave_values[1].average) /
                                     (self.parser.wave_values[1].total_average + self.wave_baselines[1])) + \
                                    ((2 * self.parser.wave_values[5].average) /
                                     (self.parser.wave_values[5].total_average + self.wave_baselines[5]))
            self.house_points[3] += ((2 * self.parser.wave_values[2].average) /
                                     (self.parser.wave_values[2].total_average + self.wave_baselines[2])) + \
                                    ((2 * self.parser.wave_values[3].average) /
                                     (self.parser.wave_values[3].total_average + self.wave_baselines[3]))

            if (self.parser.waves_values[0].total_amount - 10) % 7 == 0:
                if self.parser.waves_values[0].total_amount == 17:
                    _text = random.choice(self.on_start)
                    _frames = int(self.seconds * 60)
                elif self.parser.waves_values[0].total_amount == 45:
                    highest_house = self.house_points.index(max(self.house_points))
                    _text = self.house_quotes[highest_house][3]
                    _frames = int(self.seconds * 600)
                    _big_text = True
                else:
                    random_or_house = random.randint(0, 10)
                    if random_or_house < 5:
                        _text = random.choice(self.random)
                        while True:
                            if _text in self.used_quotes:
                                _text = random.choice(self.random)
                            else:
                                break
                        self.used_quotes.append(_text)
                        _frames = int(self.seconds * 60)
                    else:
                        highest_house = self.house_points.index(max(self.house_points))
                        _text = random.choice(self.house_quotes[highest_house])
                        while True:
                            if _text in self.used_quotes:
                                _text = random.choice(self.house_quotes[highest_house])
                            else:
                                break
                        self.used_quotes.append(_text)
                        _frames = int(self.seconds * 60)

        return _text, _frames, _big_text

    def reset(self):
        for i1 in range(0, 4):
            self.house_points[i1] = 0
        self.used_quotes = []


class SortingHat:
    def __init__(self, _speech, _width, _height, _parser):
        self.hat_sleeping = True
        self.hat_talking = False
        self.frames_left = 0
        self.text = None
        self.text_surface = None
        self.big_text = False
        self.chosen = False
        self.hat_image = pygame.image.load("img/sortinghat.png").convert()
        self.hat_image_talking = pygame.image.load("img/sortinghattalking.png").convert()
        self.hat_image_sleeping = pygame.image.load("img/sortinghatsleeping.png").convert()
        self.speechbox_big_image = pygame.image.load("img/speechboxbig.png").convert()
        self.speechbox_small_image = pygame.image.load("img/speechboxsmall.png").convert()
        self.speech = _speech
        self.text_surface = text_to_surface(random.choice(_speech.houses), True)
        self.big_text = True
        self.parser = _parser
        self.hat_transparency = 0
        self.speechbox_transparency = 0
        self.hat_image.set_alpha(self.hat_transparency)
        self.hat_image_talking.set_alpha(self.speechbox_transparency)
        self.speechbox_small_image.set_alpha(self.speechbox_transparency)
        self.speechbox_big_image.set_alpha(self.speechbox_transparency)
        self.speechbox_big_rect = self.speechbox_big_image.get_rect()
        self.speechbox_big_rect.x = int((_width - self.speechbox_big_image.get_rect().width)/2)
        self.speechbox_big_rect.y = 10
        self.speechbox_small_rect = self.speechbox_small_image.get_rect()
        self.speechbox_small_rect.x = int((_width - self.speechbox_small_image.get_rect().width) / 2)
        self.speechbox_small_rect.y = \
            self.speechbox_big_rect.y + self.speechbox_big_rect.height - self.speechbox_small_rect.height
        self.hat_rect = self.hat_image.get_rect()
        self.hat_rect.x = int((_width - self.hat_image.get_rect().width)/2)
        self.hat_rect.y = self.speechbox_big_rect.height + 10

    def reset(self):
        self.hat_sleeping = True
        self.hat_talking = False
        self.frames_left = 0
        self.chosen = False

    def set_sleeping(self, is_sleeping):
        self.hat_sleeping = is_sleeping

    def set_talking(self, is_talking):
        self.hat_talking = is_talking

    def draw(self, _window, _width, _height):    # left 80% of screen
        if not self.chosen and not self.hat_talking:
            self.text, self.frames_left, sbig_text = self.speech.update()
            if self.big_text:
                self.chosen = True
            if self.frames_left != 0:
                self.text_surface = text_to_surface(self.text, self.big_text)
                self.hat_talking = True

        if self.hat_talking:
            self.frames_left -= 1
            if self.frames_left == 0:
                self.hat_talking = False

        if self.hat_sleeping:
            if self.hat_transparency > 0:
                self.hat_transparency -= 5
        else:
            if self.hat_transparency < 255:
                self.hat_transparency += 5

        if self.hat_talking:
            if self.speechbox_transparency < 255:
                self.speechbox_transparency += 15
        else:
            if self.speechbox_transparency > 0:
                self.speechbox_transparency -= 15

        self.hat_image.set_alpha(self.hat_transparency)
        self.speechbox_big_image.set_alpha(self.speechbox_transparency)
        self.speechbox_small_image.set_alpha(self.speechbox_transparency)
        self.hat_image_talking.set_alpha(self.speechbox_transparency)
        if self.text_surface is not None:
            self.text_surface.set_alpha(self.speechbox_transparency)

        if self.big_text:
            _window.blit(self.speechbox_big_image, self.speechbox_big_rect)
        else:
            _window.blit(self.speechbox_small_image, self.speechbox_small_rect)
        _window.blit(self.hat_image_sleeping, self.hat_rect)
        _window.blit(self.hat_image, self.hat_rect)
        _window.blit(self.hat_image_talking, self.hat_rect)
        if self.text_surface is not None:
            if self.big_text:
                _window.blit(self.text_surface,
                             (int(self.speechbox_big_rect.x +
                                  (self.speechbox_big_rect.width - self.text_surface.get_width()) / 2),
                              int(self.speechbox_big_rect.y +
                                  (self.speechbox_big_rect.height - 60 - self.text_surface.get_height()) / 2)))
            else:
                _window.blit(self.text_surface,
                             (int(self.speechbox_small_rect.x +
                                  (self.speechbox_small_rect.width - self.text_surface.get_width()) / 2),
                              int(self.speechbox_small_rect.y +
                                  (self.speechbox_small_rect.height - 100 - self.text_surface.get_height()) / 2)))


def draw_waves(_window, _width, _height, _parser, _speech, _wave_renders, _wave_changes):      # right 20% of screen
    clear_window(_window, _width - 300, 0, 300, _height)
    indent = 300
    temp_x = _width - indent
    temp_y = 0
    _window.blit(_wave_renders[8], (temp_x + int((indent - _wave_renders[8].get_width())/2), temp_y))
    temp_y += _wave_renders[8].get_height() + 10
    for i1 in range(0, 8):
        _window.blit(_wave_renders[i1], (temp_x + int((indent - _wave_renders[i1].get_width())/2), temp_y))
        temp_y += _wave_renders[i1].get_height()
        average = (_speech.wave_baselines[i1] + _parser.waves_values[i1].total_average) / 2
        percentage = _parser.waves_values[i1].get_last() / average
        wave_change = _wave_changes[7]
        if percentage > 200:
            wave_change = _wave_changes[6]
        elif percentage > 150:
            wave_change = _wave_changes[5]
        elif percentage > 100:
            wave_change = _wave_changes[4]
        elif percentage == 100:
            wave_change = _wave_changes[3]
        elif percentage > 80:
            wave_change = _wave_changes[2]
        elif percentage > 40:
            wave_change = _wave_changes[1]
        elif percentage > 0:
            wave_change = _wave_changes[0]
        _window.blit(wave_change, (temp_x + int((indent - wave_change.get_width()) / 2), temp_y))
        temp_y += wave_change.get_height() + 20


def draw_signal(_window, _width, _height, _parser):     # down left corner
    _signal = _parser.signal.get_last()
    _attention = _parser.attention.get_last()
    _meditation = _parser.attention.get_last()
    if _signal == -1:
        _signal = 200
        _attention = 0
        _meditation = 0
    signal_text = font_small.render("Signal strength: " + str(int((200 - _signal)/2)) + "/100", True, c.white)
    attention_text = font_small.render("Attention: " + str(_attention) + "/100", True, c.white)
    meditation_text = font_small.render("Meditation: " + str(_meditation) + "/100", True, c.white)
    clear_window(_window, 5,
                 height - signal_text.get_height() - attention_text.get_height() - meditation_text.get_height() - 10,
                 signal_text.get_width() + 20,
                 signal_text.get_height() + attention_text.get_height() + meditation_text.get_height() + 10)
    _window.blit(signal_text, (5, height - signal_text.get_height()))
    _window.blit(attention_text,
                 (5, height - signal_text.get_height() - meditation_text.get_height() - attention_text.get_height()))
    _window.blit(meditation_text, (5, height - signal_text.get_height() - attention_text.get_height()))
    return _signal


pygame.init()
width = WIDTH
height = HEIGHT
title = "Sorting Hat for MindWave"

window = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
pygame.display.set_caption(title)
clock = pygame.time.Clock()

font_small = pygame.font.Font("fonts/pixelatus.ttf", 25)
font_smallm = pygame.font.Font("fonts/pixelatus.ttf", 35)
font_medium = pygame.font.Font("fonts/pixelatus.ttf", 50)
font_big = pygame.font.Font("fonts/pixelatus.ttf", 220)

p = MindWaveParser()
c = Colors()
s = SpeechOperator(p)
hat = SortingHat(s, width - 300, height, p)

wave_renders = []
for i in range(0, 8):
    wave_renders.append(font_small.render(p.waves[i], True, c.white))
wave_renders.append(font_smallm.render("Waves:", True, c.white))

wave_changes_renders = [font_smallm.render("- - -", True, c.red),
                        font_smallm.render("- -", True, c.medred),
                        font_smallm.render("-", True, c.darkred),
                        font_smallm.render("+/-", True, c.cyan),
                        font_smallm.render("+", True, c.green),
                        font_smallm.render("+ +", True, c.medgreen),
                        font_smallm.render("+ + +", True, c.lightgreen),
                        font_smallm.render("?", True, c.yellow)]

sleeping_frames = 0
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit(0)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.set_mode((width, height), pygame.FULLSCREEN)
                pygame.mouse.set_visible(False)
            elif event.key == pygame.K_ESCAPE:
                pygame.display.set_mode((width, height))
                pygame.mouse.set_visible(True)
            elif event.key == pygame.K_LEFT:    # DELETE
                hat.set_sleeping(not hat.hat_sleeping)
            elif event.key == pygame.K_RIGHT:
                hat.set_talking(not hat.hat_talking)

    window.fill(c.black5)
    signal = draw_signal(window, width, height, p)
    if signal < 10:
        hat.set_sleeping(False)
        sleeping_frames = 0
    else:
        hat.set_talking(False)
        hat.set_sleeping(True)
        sleeping_frames += 1

    if sleeping_frames >= 600:
        sleeping_frames = 0
        s.reset()
        p.reset()
        hat.reset()

    draw_waves(window, width, height, p, s, wave_renders, wave_changes_renders)
    hat.draw(window, width, height)
    pygame.display.flip()
    clock.tick(60)
