#!/usr/bin/env python

import binascii # Used for high scores
import datetime # Used for length of play
import os # Used to verify if high score file exists
import argparse # Used for command line argument interpretation
import curses 
from ast import literal_eval # Used to read the files
from curses import KEY_RIGHT, KEY_LEFT, KEY_UP, KEY_DOWN, KEY_RESIZE # Used for lazyness
from random import randint, choice # Used for making decisions about placing food

parser = argparse.ArgumentParser(description="Snake game that can be used with maps. Written using Python and ncurses.\n\nControl your snake with the arrow keys. Press 'q' to quit. Press space to pause.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-b", "--boundaries", help="Whether or not your game will end if you run into the borders.", default=False, action="store_true")
parser.add_argument("-c", "--cross", help="Allows the game to end if your snake turns directly behind itself.", default=False, action="store_true")
parser.add_argument("-d", "--dimensions", help="Dimensions in the format HEIGHTxLENGTH. If you are using a map, this value is ignored.", metavar="20x25", type=str)
parser.add_argument("-e", "--no-direction", help="Don't show the direction that the snake is going in.", default=False, action="store_true")
parser.add_argument("-l", "--layout", help="Instead of using the arrow keys, use the layout defined in layout. Accepted layouts are wasd and vim (hjkl).", type=str, choices=['wasd','vim'])
parser.add_argument("-m", "--more-food-types", help="Place more types of food on the screen. This places ice cream, which gives you fifteen points and makes your snake grow by ten, and cherries, which are very rare and give you ten points and half the size of your snake.", default=False, action="store_true")
parser.add_argument("map", help="Map file generated with rendermap.py.", nargs="?", default="map")
parser.add_argument("-n", "--number-of-food", help="How much food to put on the screen at a time.", default=1, metavar=1, type=int)
parser.add_argument("-s", "--speed", help="How fast your snake goes. Lower numbers are faster. This number is in milliseconds. Use 50 for a challenge.", default=125, metavar=125, type=int)
args = parser.parse_args()

if args.layout == "wasd":
    KEY_RIGHT = ord('d')
    KEY_LEFT = ord('a')
    KEY_UP = ord('w')
    KEY_DOWN = ord('s')
elif args.layout == "vim":
    KEY_RIGHT = ord("l")
    KEY_LEFT = ord("h")
    KEY_UP = ord("k")
    KEY_DOWN = ord("j")

# The snake moves right to begin with
key = KEY_RIGHT
# The score, the snake's growth queue and the current iteration start at 0
score = queue = frame = 0
title = "SNAKE"
# Snake's beginning co-ordinates (TODO: randomize)
snake = [[4,10], [4,9], [4,8], [4,7]]
# Character that represents the snake
snakechar = " "
# Special food items
cherry = ice_cream = []
# Game start time
start = datetime.datetime.now()
# List of pauses to be subtracted from the survival time
pauses = []

# Open our map, if given
try:
    with open(args.map,'rb') as f:
        map_ = f.read()
        mapdict = literal_eval(map_.decode('utf-8'))
        crc = binascii.crc32(map_+str(args.speed).encode('ascii') + (b'F' if args.more_food_types else b'')) & 0xffffffff #CRC of high score file, used to make sure that maps match for high scores. I add the speed to the end of the file so that maps at different speeds are unique.
    use_map = True
except IOError:
    mapdict = {}
    use_map = False # No map found.

walls = mapdict.get('wall',[])
teleporters = mapdict.get('teleporter',[])

scr = curses.initscr()
curses.start_color()

curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_RED) # snake
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_WHITE) # walls
curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK) # food
curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK) # teleporters
curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK) # cherries
curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_MAGENTA) # ice cream

maxyx = scr.getmaxyx()
length = maxyx[1]
height = maxyx[0]

if use_map or args.dimensions:
    if use_map:
        h,l = mapdict['dimensions']
    else: #args.dimensions
        try:
            h,l = [int(a) for a in args.dimensions.split('x')]
        except:
            curses.endwin()
            raise ValueError("Your DIMENSIONS argument is improperly formatted. Please see help.")
    if h > height or l > length:
        curses.endwin()
        raise ValueError("Specified dimensions bigger than screen.")
    if h < 5 or l < 10:
        curses.endwin()
        raise ValueError("Map too small!")
    else:
        length = l+2 #compensate for border
        height = h+2

total_blocks = (length-2) * (height-2)

if (total_blocks-len(snake)) <= args.number_of_food: 
    curses.endwin()
    raise ValueError("The game is unplayable with that many food!")

win = curses.newwin(height, length, 0, 0)
win.keypad(1)
curses.noecho()
curses.curs_set(0)
win.border(0)
win.nodelay(1)
#Put title in the top center
win.addstr(0, int((length/2)-(len(title)/2)), title) 

def psnake(y, x, snakechar):
    win.addch(y, x, snakechar, curses.color_pair(1))

def pfood(number_of_food,not_empty_blocks,food,type="normal"):
    for x in range(0,number_of_food):
        success = False
        while not success:
            food.append([randint(1, height-2), randint(1, length-2)])
            #If the food is not in the snake, the walls, or in another food
            if food[-1] in not_empty_blocks or food.count(food[-1]) == 2:
                del food[-1]
            else:
                success = True
        if type == "normal":
            char = "@"
            color = 3
        elif type == "cherry":
            char = "o"
            color = 5
            food[-1].append(150) # "Life" of the cherry. In fifty moves of the snake head, the cherry is gone.
        else: # type == "ice_cream"
            char = "^"
            color = 6
            food[-1].append(300)

        win.addch(food[-1][0], food[-1][1], char, curses.color_pair(color)) # Prints the food
    return food

food = pfood(args.number_of_food,snake+walls+teleporters,[])

if use_map:
    for coords in walls:
        win.addch(coords[0], coords[1], ' ', curses.color_pair(2))
    if len(teleporters) > 1: # Don't place any teleporters if there is only one teleporter
        for coords in teleporters:
            win.addch(coords[0], coords[1], '?', curses.color_pair(4))

while True:
    frame += 1
    win.addstr(height-1, 2, 'Score : {0}'.format(score)) # Printing 'Score'
    prevKey = key
    key = win.getch()

    win.timeout(args.speed)

    if key == ord(' '): # If SPACE BAR is pressed, wait for another one (Pause/Resume)
        key = -1 # 
        # When you pause the game time should also pause
        start_pause = datetime.datetime.now()
        while key not in [ord(' '),ord('q')]: 
            key = win.getch()
        end_pause = datetime.datetime.now()
        pauses.append(end_pause-start_pause)

    if key == KEY_RESIZE or key == ord('q'):
        break

    if key not in [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]: # If an invalid key is pressed
        key = prevKey
    
    if not args.cross:
        if key == KEY_DOWN and prevKey == KEY_UP \
        or key == KEY_UP and prevKey == KEY_DOWN \
        or key == KEY_LEFT and prevKey == KEY_RIGHT \
        or key == KEY_RIGHT and prevKey == KEY_LEFT: key = prevKey

    if not args.no_direction: snakechar = "v" if key == KEY_DOWN else ("<" if key == KEY_LEFT else (">" if key == KEY_RIGHT else "^"))  

    if frame == 1: #On the first frame
        for x in range(0,len(snake)): 
            psnake(snake[x][0], snake[x][1], snakechar) #Put the whole snake on the screen

    # Calculates the new coordinates of the head of the snake. NOTE: len(snake) increases.
    # This is taken care of later at [1].
    snake.insert(0, [snake[0][0] + (key == KEY_DOWN and 1) + (key == KEY_UP and -1), snake[0][1] + (key == KEY_LEFT and -1) + (key == KEY_RIGHT and 1)])

    # Exit if snake crosses the boundaries
    if args.boundaries:
        if snake[0][0] == 0 or snake[0][0] == length-1 or snake[0][1] == 0 or snake[0][1] == height-1: break
    # If snake crosses the boundaries, make it enter from the other side
    if snake[0][0] == 0: snake[0][0] = height-2
    if snake[0][1] == 0: snake[0][1] = length-2
    if snake[0][0] == height-1: snake[0][0] = 1
    if snake[0][1] == length-1: snake[0][1] = 1


    # If snake runs over itself
    if snake[0] in snake[1:]: break
    # If snake runs into a wall ;_;
    if snake[0] in walls: break

    if snake[0] in teleporters and len(teleporters) > 1:
        otherteleporters = [teleporter for teleporter in teleporters if teleporter != snake[0]]
        snake[0] = [x+choice([-1,1]) for x in choice(otherteleporters)]
    
    not_empty_blocks = snake+walls+teleporters+food+ice_cream+cherry

    # Yes, this is possible. If there are no empty blocks, the game is over. You win!
    if len(not_empty_blocks) > total_blocks: break

    if args.more_food_types:
        not_empty_blocks += cherry+ice_cream
        die = randint(1,1000) # Like a six-sided die, silly. Except 100 sided.
        foodcoords = [f[:2] for f in food]
        if frame > 500: # Special food may not appear in the beginning
            if die == 6 and cherry == []:
                cherry = pfood(1,not_empty_blocks,[],type="cherry")
            elif cherry != []: # If there's a cherry on the screen
                cherry[0][2] -= 1 # Decrease the cherry's life
                if cherry[0][2] == 0: # When the cherry dies
                    win.addch(cherry[0][0], cherry[0][1], ' ')
                    cherry = []
                if len(cherry) > 0 and snake[0] == cherry[0][:2]: # If there's a cherry and the snake eats it
                    score += 10
                    cherry = []
                    for x in range(0,int(len(snake)/2)): # Cut the snake in half
                        tail = snake.pop()
                        win.addch(tail[0], tail[1], ' ')
            if die <= 3 and ice_cream == []:
                ice_cream = pfood(1,not_empty_blocks,[],type="ice_cream")
            elif ice_cream != []:
                ice_cream[0][2] -= 1
                if ice_cream[0][2] == 0:
                    win.addch(ice_cream[0][0], ice_cream[0][1], ' ')
                    ice_cream = []
                if len(ice_cream) > 0 and snake[0] == ice_cream[0][:2]:
                    score += 20
                    queue += 20
                    ice_cream = []

    if snake[0] in (foodcoords if args.more_food_types else food):  # When snake eats the food
        score += 1
        if args.more_food_types:
            food.pop(foodcoords.index(snake[0]))
        else:
            food.remove(snake[0]) 
        food = pfood(1,not_empty_blocks,food)
    else:    
        if queue > 0: # Snake growth queue imposed by ice cream
            queue -= 1
        else:
            last = snake.pop() # [1] If it does not eat the food, length decreases
            win.addch(last[0], last[1], ' ')

    psnake(snake[0][0], snake[0][1], snakechar)

curses.endwin()
end = datetime.datetime.now()
delta = end - start
for pause in pauses: delta -= pause

#High scores
scores = {}
filename = ".snakescores"

if not use_map:
    crc = "N{0}{1}{2}{3}".format(height,length,args.speed,"" if not args.more_food_types else "F") #Yes, I know, this isn't really a "CRC". Sue me.

if not os.path.exists(filename):
    with open(filename,"w") as f:
        pass

def scores_():
    try:
        scores[crc].append(score)
        scores[crc].sort()
        scores[crc].reverse()
        scores[crc] = scores[crc][:10] #Only save the highest ten scores.
    except KeyError:
        scores[crc] = [score]

with open(filename,"r+") as f:
    try:
        scores = literal_eval(f.read())
        scores_()
    except Exception: #Something went wrong, the file may be corrupt or non-existent.
        scores_()
    finally:
        f.seek(0)
        f.truncate()
        f.write(str(scores))

if key == KEY_RESIZE: print("Window may not be resized during gameplay. This is a feature, not a bug.")
high_score = max(scores[crc]) 
print("Score - {0}{1}{2}".format('\033[92m' if score >= high_score else '\033[91m', score, '\033[0m'))
print("You survived {0:d} seconds. ({1:02d}:{2:02d})".format(delta.seconds, int(delta.seconds/60), delta.seconds%60))
if score == high_score: print("New high score!")

if use_map:
    print("Map file {0} in use, CRC {1}. Scores are attached to this map file and speed.".format(args.map, crc))
print("High scores for games played with window dimensions of {0}x{1}, a speed of {2} ({3}) and {4} special food enabled:".format(height, length, args.speed, "Hard" if args.speed <= 75 else ("Normal" if args.speed <= 125 else "Easy"), "with" if args.more_food_types else "without"))

for x, score in enumerate(scores[crc],1):
    print("{0}. {1}".format(x,score))
