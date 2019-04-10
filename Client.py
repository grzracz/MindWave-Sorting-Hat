import socket
import threading
import pygame
import random
import winsound
import math
import datetime
import os

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
        while True:
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
        self.on_start_sounds = [
            [
                "sound/on_start/whereshalli1.wav",
                "sound/on_start/whereshalli2.wav"
            ],
            [
                "sound/on_start/thisisinteresting1.wav"
            ],
            [
                "sound/on_start/verydifficult1.wav"
            ],
            [
                "sound/on_start/areyouafraid1.wav",
                "sound/on_start/areyouafraid2.wav"
            ],
            [
                "sound/on_start/dontworry1.wav",
                "sound/on_start/dontworry2.wav"
            ]
        ]

        self.random = ["Ah, right then.",
                       "Hmm, okay...",
                       "I think I know what to do with you..."]
        self.random_sounds = [
            [
                "sound/random/ahrightthen1.wav",
                "sound/random/ahrightthen2.wav"
            ],
            [
                "sound/random/hmmokay1.wav",
                "sound/random/hmmokay2.wav",
                "sound/random/hmmokay3.wav"
            ],
            [
                "sound/random/ithinkiknow1.wav"
            ]
        ]

        self.house_quotes = []
        self.house_quotes_sounds = []
        for i1 in range(0, 4):
            self.house_quotes.append([])
            self.house_quotes_sounds.append([])
        self.house_quotes[0] = ["Plenty of courage...",
                                "Yes... very brave.",
                                "You have a lot of nerve!",
                                "GRYFFINDOR!"]
        self.house_quotes_sounds[0] = [
            [
                "sound/gryffindor/plentyofcourage1.wav"
            ],
            [
                "sound/gryffindor/yesverybrave1.wav"
            ],
            [
                "sound/gryffindor/alotofnerve1.wav"
            ],
            [
                "sound/gryffindor/gryffindor1.wav",
                "sound/gryffindor/gryffindor2.wav"
            ]
        ]

        self.house_quotes[1] = ["Patient and loyal...",
                                "Hard work will get you far.",
                                "Strong sense of justice...",
                                "HUFFLEPUFF!"]
        self.house_quotes_sounds[1] = [
            [
                "sound/hufflepuff/patientandloyal1.wav"
            ],
            [
                "sound/hufflepuff/hardwork1.wav"
            ],
            [
                "sound/hufflepuff/strongsenseofjustice1.wav",
                "sound/hufflepuff/strongsenseofjustice2.wav"
            ],
            [
                "sound/hufflepuff/hufflepuff1.wav",
                "sound/hufflepuff/hufflepuff2.wav"
            ]
        ]

        self.house_quotes[2] = ["Not a bad mind.",
                                "There's talent! Interesting...",
                                "Quite smart...",
                                "RAVENCLAW!"]
        self.house_quotes_sounds[2] = [
            [
                "sound/ravenclaw/notabadmind1.wav",
                "sound/ravenclaw/notabadmind2.wav"
            ],
            [
                "sound/ravenclaw/therestalent1.wav",
                "sound/ravenclaw/therestalent2.wav"
            ],
            [
                "sound/ravenclaw/quitesmart1.wav",
                "sound/ravenclaw/quitesmart2.wav"
            ],
            [
                "sound/ravenclaw/ravenclaw1.wav",
                "sound/ravenclaw/ravenclaw2.wav"
            ]
        ]

        self.house_quotes[3] = ["A nice thirst to prove yourself.",
                                "Quite ambitious, yes...",
                                "Great sense of self-preservation...",
                                "SLYTHERIN!"]
        self.house_quotes_sounds[3] = [
            [
                "sound/slitherin/anicethirst1.wav"
            ],
            [
                "sound/slitherin/quiteambitious1.wav",
                "sound/slitherin/quiteambitious2.wav"
            ],
            [
                "sound/slitherin/greatsenseofself1.wav",
                "sound/slitherin/greatsenseofself2.wav"
            ],
            [
                "sound/slitherin/slitherin1.wav",
                "sound/slitherin/slitherin2.wav"
            ]
        ]

        self.seconds = 3
        self.used_quotes = []
        self.parser = _parser
        self.last_amount = self.parser.attention.total_amount
        self.house_points = []  # Gryffindor, Hufflepuff, Ravenclaw, Slytherin
        for i1 in range(0, 4):
            self.house_points.append(0)

    def update(self, only_points):
        _text = None
        _frames = 0
        _big_text = False
        if self.last_amount != self.parser.attention.total_amount and self.parser.waves_values[0].total_amount > 10:
            self.last_amount = self.parser.attention.total_amount
            self.house_points[0] += ((2 * self.parser.waves_values[6].average) /
                                     (self.parser.waves_values[6].total_average + self.wave_baselines[6])) + \
                                    ((2 * self.parser.waves_values[7].average) /
                                     (self.parser.waves_values[7].total_average + self.wave_baselines[7]))
            self.house_points[1] += ((2 * self.parser.waves_values[0].average) /
                                     (self.parser.waves_values[0].total_average + self.wave_baselines[0])) + \
                                    ((2 * self.parser.waves_values[4].average) /
                                     (self.parser.waves_values[4].total_average + self.wave_baselines[4]))
            self.house_points[2] += ((2 * self.parser.waves_values[1].average) /
                                     (self.parser.waves_values[1].total_average + self.wave_baselines[1])) + \
                                    ((2 * self.parser.waves_values[5].average) /
                                     (self.parser.waves_values[5].total_average + self.wave_baselines[5]))
            self.house_points[3] += ((2 * self.parser.waves_values[2].average) /
                                     (self.parser.waves_values[2].total_average + self.wave_baselines[2])) + \
                                    ((2 * self.parser.waves_values[3].average) /
                                     (self.parser.waves_values[3].total_average + self.wave_baselines[3]))
            print("House points: Gryffindor (" + str(self.house_points[0])
                  + "), Hufflepuff (" + str(self.house_points[1])
                  + "), Ravenclaw (" + str(self.house_points[2])
                  + "), Slytherin (" + str(self.house_points[3]) + ")")

            if (self.parser.waves_values[0].total_amount - 10) % 6 == 0 and not only_points:
                if self.parser.waves_values[0].total_amount == 16:
                    _text = random.choice(self.on_start)
                    index = self.on_start.index(_text)
                    winsound.PlaySound(random.choice(self.on_start_sounds[index]), winsound.SND_ASYNC)
                    _frames = int(self.seconds * 60)
                elif self.parser.waves_values[0].total_amount == 40:
                    highest_house = self.house_points.index(max(self.house_points))
                    _text = self.house_quotes[highest_house][3]
                    winsound.PlaySound(random.choice(self.house_quotes_sounds[highest_house][3]), winsound.SND_ASYNC)
                    _frames = int(self.seconds * 60 * 3)
                    _big_text = True
                else:
                    random_or_house = random.randint(0, 10)
                    if random_or_house < 2:
                        _text = random.choice(self.random)
                        while True:
                            if _text in self.used_quotes:
                                _text = random.choice(self.random)
                            else:
                                break
                        self.used_quotes.append(_text)
                        index = self.random.index(_text)
                        winsound.PlaySound(random.choice(self.random_sounds[index]), winsound.SND_ASYNC)
                        _frames = int(self.seconds * 60)
                    else:
                        highest_house = self.house_points.index(max(self.house_points))
                        random_house_quote = random.randint(0, 2)
                        _text = self.house_quotes[highest_house][random_house_quote]
                        while True:
                            if _text in self.used_quotes:
                                random_house_quote = random.randint(0, 2)
                                _text = self.house_quotes[highest_house][random_house_quote]
                            else:
                                break
                        self.used_quotes.append(_text)
                        index = self.house_quotes[highest_house].index(_text)
                        winsound.PlaySound(random.choice(self.house_quotes_sounds[highest_house][index]),
                                           winsound.SND_ASYNC)
                        _frames = int(self.seconds * 60)

        if not only_points:
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
        if not self.chosen:
            if not self.hat_talking:
                self.text, self.frames_left, self.big_text = self.speech.update(self.hat_talking)
            else:
                self.speech.update(self.hat_talking)
            if self.big_text:
                self.chosen = True
                save_to_logs(self.speech, self.parser)
            if not self.hat_talking:
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

        if self.big_text:
            _window.blit(self.speechbox_big_image, self.speechbox_big_rect)
        else:
            _window.blit(self.speechbox_small_image, self.speechbox_small_rect)
        _window.blit(self.hat_image_sleeping, self.hat_rect)
        _window.blit(self.hat_image, self.hat_rect)
        _window.blit(self.hat_image_talking, self.hat_rect)
        if self.text_surface is not None and self.speechbox_transparency > 64:
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
    indent = 300
    clear_window(_window, _width - indent, 0, indent, _height)
    temp_x = _width - indent
    temp_y = 0
    _window.blit(_wave_renders[8], (temp_x + int((indent - _wave_renders[8].get_width())/2), temp_y))
    temp_y += _wave_renders[8].get_height() + 10
    for i1 in range(0, 8):
        _window.blit(_wave_renders[i1], (temp_x + int((indent - _wave_renders[i1].get_width())/2), temp_y))
        temp_y += _wave_renders[i1].get_height()
        average = (_speech.wave_baselines[i1] + _parser.waves_values[i1].total_average) / 2
        percentage = _parser.waves_values[i1].get_last() * 100 / average
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
    _meditation = _parser.meditation.get_last()
    if _signal == -1 or _signal == 200:
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


def save_to_logs(speech, parser):
    file = open("Logs.txt", "a")
    file.write(str(datetime.datetime.now()) + "\n")
    file.write("House points:\n")
    house_list = []
    for x1 in range(0, 4):
        house_list.append((speech.houses[x1], speech.house_points[x1]))
    for x1 in range(0, 4):
        file.write(house_list[x1][0] + ": " + str(house_list[x1][1]) + "\n")
    file.write("Waves: \n")
    for x1 in range(0, 8):
        file.write(parser.waves[x1] + ": " + str(parser.waves_values[x1].total_average) + "\n")
    file.write("\n")
    file.close()


class Candles:
    def __init__(self, attention, meditation):
        self.candle_unlit = pygame.image.load("img/candleunlit.png").convert()
        self.candle1 = pygame.image.load("img/candle1.png").convert()
        self.candle2 = pygame.image.load("img/candle2.png").convert()
        self.flame_transparency = 0
        self.candle_width = self.candle1.get_width()
        self.candle_height = self.candle1.get_height()
        self.candles = []
        self.amount = 0
        self.candle_switch = False
        self.attention = attention
        self.meditation = meditation
        self.lit = False
        self.alpha = 0
        self.one_degree = math.pi / 180

    def set_lit(self, is_lit):
        self.lit = is_lit

    def add(self, _x, _y, _r_x, _r_y, _degree, _left, _speed):
        self.candles.append([_x, _y, _r_x, _r_y, _degree * self.one_degree, _left, _speed, 0])
        self.amount += 1

    def draw(self, _window):
        attention_value = self.attention.get_last()
        if self.lit:
            if self.flame_transparency < 28 + attention_value:
                self.flame_transparency += 5
            elif self.flame_transparency < 155 + attention_value and self.candle_switch:
                self.flame_transparency += 3
                if self.flame_transparency >= 155 + attention_value:
                    self.candle_switch = not self.candle_switch
            else:
                self.flame_transparency -= 3
                if self.flame_transparency <= 28 + attention_value:
                    self.candle_switch = not self.candle_switch
        else:
            if self.flame_transparency > 0:
                self.flame_transparency -= 5

        self.candle1.set_alpha(self.flame_transparency)
        self.candle2.set_alpha(self.flame_transparency)
        speed_modifier = 1 - self.meditation.get_last()/100

        for i1 in range(0, self.amount):
            clear_window(_window, self.candles[i1][0], self.candles[i1][1],
                         int(2 * self.candles[i1][2] + self.candle_width),
                         int(2 * self.candles[i1][3] + self.candle_height))
            temp_x = self.candles[i1][0] + self.candles[i1][2] + int(
                self.candles[i1][2] * math.cos(self.candles[i1][4]) * (-1 if self.candles[i1][5] else 1))
            temp_y = self.candles[i1][1] + self.candles[i1][3] + int(
                self.candles[i1][3] * math.sin(self.candles[i1][4]))
            self.candles[i1][4] += self.one_degree / self.candles[i1][6] * speed_modifier
            _window.blit(self.candle_unlit, (temp_x, temp_y))
            if self.candles[i1][5]:
                _window.blit(self.candle1, (temp_x, temp_y)) if self.candle_switch \
                    else _window.blit(self.candle2, (temp_x, temp_y))
            else:
                _window.blit(self.candle2, (temp_x, temp_y)) if self.candle_switch \
                    else _window.blit(self.candle1, (temp_x, temp_y))


pygame.init()
width = WIDTH
height = HEIGHT
title = "Sorting Hat for MindWave"

os.putenv('SDL_VIDEO_WINDOW_POS', '0,0')
window = pygame.display.set_mode((width, height), pygame.NOFRAME)
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
candles = Candles(p.attention, p.meditation)

min_speed = 2
max_speed = 4
ellipse_width = 5
ellipse_height = 70

candles.add(150, 10, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(460, 180, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(780, 30, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(1110, 150, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(100, 530, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(270, 770, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(1300, 500, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(1450, 800, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))
candles.add(1500, 5, ellipse_width, ellipse_height, random.randint(0, 360),
            random.choice([True, False]), random.randint(min_speed, max_speed))

wave_renders = []
for i in range(0, 8):
    color = c.white
    if p.waves[i] == "Delta" or p.waves[i] == "low Beta":
        color = c.brown
    if p.waves[i] == "Theta" or p.waves[i] == "high Beta":
        color = c.blue
    if p.waves[i] == "low Alpha" or p.waves[i] == "high Alpha":
        color = c.green
    if p.waves[i] == "low Gamma" or p.waves[i] == "high Gamma":
        color = c.yellow

    wave_renders.append(font_small.render(p.waves[i], True, color))
wave_renders.append(font_smallm.render("Waves:", True, c.white))

wave_changes_renders = [font_smallm.render("- - -", True, c.red),
                        font_smallm.render("- -", True, c.medred),
                        font_smallm.render("-", True, c.darkred),
                        font_smallm.render("=", True, c.cyan),
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
                pygame.display.set_mode((width, height), pygame.NOFRAME)
                pygame.mouse.set_visible(False)
            elif event.key == pygame.K_ESCAPE:
                pygame.display.set_mode((width, height))
                pygame.mouse.set_visible(True)
            elif event.key == pygame.K_RIGHT:
                sleeping_frames = 0
                s.reset()
                p.reset()
                hat.reset()

    window.fill(c.black5)
    signal = draw_signal(window, width, height, p)
    if signal < 10:
        hat.set_sleeping(False)
        candles.set_lit(True)
        sleeping_frames = 0
    else:
        hat.set_talking(False)
        hat.set_sleeping(True)
        candles.set_lit(False)
        sleeping_frames += 1

    if sleeping_frames >= 300:
        sleeping_frames = 0
        s.reset()
        p.reset()
        hat.reset()

    draw_waves(window, width, height, p, s, wave_renders, wave_changes_renders)
    candles.draw(window)
    hat.draw(window, width, height)
    pygame.display.flip()
    clock.tick(60)
