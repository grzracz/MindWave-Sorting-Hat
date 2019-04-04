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
        for i in range(0, number_of_instances):
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
        for i in range(0, self.amount):
            _sum += self.instances[i]
        self.average = _sum / self.amount

    def get_last(self):
        if self.last == -1:
            return -1
        else:
            return self.instances[self.last]


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


def get_next_byte(string, last_byte):
    if string[last_byte:last_byte + 2] is "":
        return "", 0
    else:
        return string[last_byte:last_byte+2], last_byte+2


def byte_to_float(string):
    string = str(int(string[0]) - 1) + string[1:]
    return convert(string)


def convert(s):
    i = int(s, 16)
    cp = pointer(c_int(i))
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
        for i in range(0, 8):
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


def clear_window(_window, _x, _y, _width, _height):
    pygame.draw.rect(window, c.black5, pygame.Rect(_x, _y, _width, _width))


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
        for i in range(0, 4):
            self.house_quotes.append([])
        self.house_quotes[0] = ["Plenty of courage...",
                                "Yes... very brave.",
                                "You have a lot of nerve!"]

        self.house_quotes[1] = ["Patient and loyal...",
                                "Hard work will get you far.",
                                "Strong sense of justice..."]

        self.house_quotes[2] = ["Not a bad mind.",
                                "There's talent! Interesting...",
                                "Quite smart..."]

        self.house_quotes[3] = ["A nice thirst to prove yourself.",
                                "Quite ambitious, yes...",
                                "Great sense of self-preservation..."]

        self.seconds = 4
        self.used_quotes = []
        self.parser = _parser
        self.house_points = []  # Gryffindor, Hufflepuff, Ravenclaw, Slytherin
        for i in range(0, 4):
            self.house_points.append(0)

    def update(self):
        _text = ""
        _frames = 0
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
                random_or_house = random.randint(0, 10)
                if random_or_house < 4:
                    _text = random.choice(self.random)
                    _frames = int(self.seconds * 60)
                else:
                    highest_house = self.house_points.index(max(self.house_points))
                    _text = random.choice(self.house_quotes[highest_house])
                    _frames = int(self.seconds * 60)

        return _text, _frames

    def reset(self):
        for i in range(0, 4):
            self.house_points[i] = 0


class SortingHat:
    def __init__(self, _hat_image, _hat_image_sleeping, _speechbox_image, _speech, _width, _height, _parser):
        self.hat_sleeping = True
        self.hat_talking = False
        self.hat_image = _hat_image
        self.hat_image_sleeping = _hat_image_sleeping
        self.speechbox_image = _speechbox_image
        self.speech = _speech
        self.parser = _parser
        self.hat_transparency = 0
        self.speechbox_transparency = 0
        self.hat_image.set_alpha(self.hat_transparency)
        self.speechbox_image.set_alpha(self.speechbox_transparency)
        self.speechbox_rect = self.speechbox_image.get_rect()
        self.speechbox_rect.x = int((_width - self.speechbox_image.get_rect().width)/2)
        self.speechbox_rect.y = 10
        self.hat_rect = self.hat_image.get_rect()
        self.hat_rect.x = int((_width - self.hat_image.get_rect().width)/2)
        self.hat_rect.y = self.speechbox_rect.height + 10

    def reset(self):
        self.hat_sleeping = True
        self.hat_talking = False

    def set_sleeping(self, is_sleeping):
        self.hat_sleeping = is_sleeping

    def set_talking(self, is_talking):
        self.hat_talking = is_talking

    def draw(self, _window, _width, _height):    # top 80% of screen
        if self.hat_sleeping:
            if self.hat_transparency > 0:
                self.hat_transparency -= 5
        else:
            if self.hat_transparency < 255:
                self.hat_transparency += 5

        if self.hat_talking:
            if self.speechbox_transparency < 255:
                self.speechbox_transparency += 5
        else:
            if self.speechbox_transparency > 0:
                self.speechbox_transparency -= 5

        self.hat_image.set_alpha(self.hat_transparency)
        self.speechbox_image.set_alpha(self.speechbox_transparency)

        _window.blit(self.speechbox_image, self.speechbox_rect)
        _window.blit(self.hat_image_sleeping, self.hat_rect)
        _window.blit(self.hat_image, self.hat_rect)


def draw_waves(_window, _width, _height, _parser):      # bottom 20% of screen
    return 0


def draw_signal(_window, _width, _height, _parser):     # down left corner
    _signal = _parser.signal.get_last()
    if _signal == -1:
        _signal = 200
    signal_text = font_small.render("Signal strength: " + str(int((200 - _signal)/2)) + "/100", True, c.white)
    clear_window(_window, 5, height - signal_text.get_height() - 10,
                 signal_text.get_width() + 20, signal_text.get_height() + 10)
    _window.blit(signal_text, (5, height - signal_text.get_height()))
    return _signal


pygame.init()
width = WIDTH
height = HEIGHT
title = "Sorting Hat for MindWave"

window = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
pygame.display.set_caption(title)
clock = pygame.time.Clock()

width = width - 350

font_small = pygame.font.Font("fonts/pixelatus.ttf", 30)
img_sortinghat = pygame.image.load("img/sortinghat.png").convert()
img_sleepinghat = pygame.image.load("img/sortinghatsleeping.png").convert()
img_speechbox = pygame.image.load("img/speechbox.png").convert()

p = MindWaveParser()
c = Colors()
s = SpeechOperator(p)
hat = SortingHat(img_sortinghat, img_sleepinghat, img_speechbox, s, width, height, p)

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
            elif event.key == pygame.K_LEFT:
                hat.set_sleeping(not hat.hat_sleeping)
            elif event.key == pygame.K_RIGHT:
                hat.set_talking(not hat.hat_talking)

    window.fill(c.black5)
    signal = draw_signal(window, width, height, p)
    '''
    if signal < 10:
        hat.set_sleeping(False)
    else:
        hat.set_sleeping(True)
    '''
    draw_waves(window, width, height, p)

    hat.draw(window, width, height)
    pygame.display.flip()
    clock.tick(60)
