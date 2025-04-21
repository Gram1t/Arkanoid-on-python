import arcade
import random
import time
import pyglet

WIDTH = 96 * 10
HEIGHT = 1000
TITLE = 'Arkanoid'
POWERUP_PROBABILITY = 0.1  # 10% chance of powerup appearance
LEVEL_FILES = [f'levels/level{i}.txt' for i in range(1, 11)]


class PowerUp(arcade.Sprite):
    def __init__(self, texture, scale=1.5):
        super().__init__(f'images/{texture}', scale)
        self.type = texture.split('_')[1].replace('.png', '')  # green, white, red, yellow, size, unsize
        self.duration = 12  # duration of powerup effect in seconds

    def update(self, delta_time=0):
        self.center_y -= 2
        if self.bottom < 0:
            self.remove_from_sprite_lists()


class Brick(arcade.Sprite):
    def __init__(self, color, scale=1.5):
        self._color = color
        super().__init__(f'images/brick_{color}.png', scale)
        durability_mapping = {'green': 1, 'yellow': 2, 'red': 3}
        self.durability = durability_mapping[color]

    def hit(self):
        self.durability -= 1
        if self.durability == 2:
            self.texture = arcade.load_texture('images/brick_yellow.png')
        elif self.durability == 1:
            self.texture = arcade.load_texture('images/brick_green.png')
        elif self.durability <= 0:
            self.remove_from_sprite_lists()
            if random.random() < POWERUP_PROBABILITY:
                return self.create_powerup()

    def create_powerup(self):
        powerup_textures = ['power_green.png', 'power_white.png', 'power_red.png', 'power_yellow.png', 'power_size.png',
                            'power_unsize.png']
        powerup_texture = random.choice(powerup_textures)
        powerup = PowerUp(powerup_texture)
        powerup.center_x = self.center_x
        powerup.center_y = self.center_y
        return powerup


class Ball(arcade.Sprite):
    def __init__(self, start_attached=True, change_x=0, change_y=0, speed=7):
        super().__init__('images/ball.png')
        self.change_x = change_x
        self.change_y = change_y
        self.speed = speed
        self.should_stick = False
        self.stuck = start_attached
        self.attached_to_paddle = False

    def start_moving(self):
        self.change_x = random.choice([1, -1])
        self.change_y = 1
        self.stuck = False
        self.attached_to_paddle = False

    def stick_to_paddle(self, paddle):
        if self.stuck:
            self.center_x = paddle.center_x
            self.center_y = paddle.top + self.height // 2

    def update(self, delta_time=0):
        if not self.stuck:
            self.center_x += self.change_x * self.speed
            self.center_y += self.change_y * self.speed
        if self.top >= HEIGHT:
            self.change_y = -1
        if self.right >= WIDTH:
            self.change_x = -1
        if self.left <= 0:
            self.change_x = 1
        if self.bottom <= 0:
            self.remove_from_sprite_lists()


class Paddle(arcade.Sprite):
    def __init__(self, texture, scale=1.5):
        super().__init__(f'images/{texture}', scale)
        self.change_x = 0
        self.speed = 7
        self.original_scale = float(scale)  # ensure original_scale is a float
        self.scale_factor = float(scale)  # Store current scale factor value
        self.update_hitboxes()

    def update_hitboxes(self):
        self.left_hitbox = arcade.SpriteCircle(self.width // 6, arcade.color.RED)
        self.left_hitbox.center_x = self.center_x - self.width // 3
        self.left_hitbox.center_y = self.center_y
        self.center_hitbox = arcade.SpriteCircle(self.width // 6, arcade.color.GREEN)
        self.center_hitbox.center_x = self.center_x
        self.center_hitbox.center_y = self.center_y
        self.right_hitbox = arcade.SpriteCircle(self.width // 6, arcade.color.BLUE)
        self.right_hitbox.center_x = self.center_x + self.width // 3
        self.right_hitbox.center_y = self.center_y

    def on_update(self, delta_time=0):
        self.center_x += self.change_x * self.speed
        if self.left <= 0:
            self.change_x = 0
            self.left = 0
        elif self.right >= WIDTH:
            self.change_x = 0
            self.right = WIDTH
        self.update_hitboxes()

    def check_collision_with_ball(self, ball):
        if arcade.check_for_collision(ball, self.left_hitbox):
            ball.change_x = -abs(ball.change_x)
            ball.change_y = 1
        elif arcade.check_for_collision(ball, self.right_hitbox):
            ball.change_x = abs(ball.change_x)
            ball.change_y = 1
        elif arcade.check_for_collision(ball, self.center_hitbox):
            ball.change_y = 1
        ball.bottom = self.top + 1


class AnimatedBackground:
    def __init__(self, background_gif):
        anim = pyglet.image.load_animation(background_gif)
        self.sprite = pyglet.sprite.Sprite(anim)
        self.sprite.scale = max(WIDTH / self.sprite.width, HEIGHT / self.sprite.height)

    def draw(self):
        self.sprite.draw()


class Arkanoid(arcade.Window):
    def __init__(self):
        super().__init__(WIDTH, HEIGHT, TITLE)
        self.level_index = 0  # Current level index
        self.balls = arcade.SpriteList()
        self.ball = Ball(start_attached=True)
        self.ball.center_x = WIDTH // 2
        self.ball.center_y = 50
        self.ball.attached_to_paddle = True
        self.balls.append(self.ball)
        self.paddle = Paddle('paddle.png')
        self.paddle.center_x = WIDTH // 2
        self.paddle.bottom = 0
        self.bricks = arcade.SpriteList()
        self.powerups = arcade.SpriteList()
        self.active_powerups = []  # list of active powerups with their end times
        self.background = AnimatedBackground('images/background1.gif')
        self.load_level(self.level_index)
        self.all_sprites = arcade.SpriteList()
        self.all_sprites.append(self.paddle)
        self.all_sprites.extend(self.balls)
        self.all_sprites.extend(self.bricks)
        self.all_sprites.extend(self.powerups)

        # Add background music
        self.background_music = pyglet.media.load('music/background.mp3', streaming=False)
        self.background_music_player = pyglet.media.Player()
        self.background_music_player.queue(self.background_music)
        self.background_music_player.loop = True
        self.background_music_player.volume = 0.35  # Volume at 35%
        self.background_music_player.play()

    def load_level(self, level_index):
        level_file_path = LEVEL_FILES[level_index]
        with open(level_file_path) as level_file:
            for row, line in enumerate(level_file):
                for col, char in enumerate(line.strip()):
                    if char == '1':
                        color = 'green'
                    elif char == '2':
                        color = 'yellow'
                    elif char == '3':
                        color = 'red'
                    else:
                        continue
                    brick = Brick(color)
                    brick.left = col * brick.width
                    brick.top = HEIGHT - (row + 1) * brick.height
                    self.bricks.append(brick)

    def next_level(self):
        self.level_index += 1
        if self.level_index < len(LEVEL_FILES):
            self.balls = arcade.SpriteList()
            self.ball = Ball(start_attached=True)
            self.ball.center_x = WIDTH // 2
            self.ball.center_y = 50
            self.ball.attached_to_paddle = True
            self.balls.append(self.ball)
            self.paddle = Paddle('paddle.png')
            self.paddle.center_x = WIDTH // 2
            self.paddle.bottom = 0
            self.bricks = arcade.SpriteList()
            self.powerups = arcade.SpriteList()
            self.active_powerups = []  # list of active powerups with their end times
            self.load_level(self.level_index)
            self.all_sprites = arcade.SpriteList()
            self.all_sprites.append(self.paddle)
            self.all_sprites.extend(self.balls)
            self.all_sprites.extend(self.bricks)
            self.all_sprites.extend(self.powerups)
        else:
            print('>> Well Done, you completed all levels!')
            arcade.close_window()

    def on_update(self, dt):
        current_time = time.time()
        self.active_powerups = [p for p in self.active_powerups if p['end_time'] > current_time]
        for ball in self.balls:
            if ball.stuck and ball.attached_to_paddle:
                ball.stick_to_paddle(self.paddle)
            else:
                ball.update()
        for ball in self.balls:
            bricks_hit_list = arcade.check_for_collision_with_list(ball, self.bricks)
            if bricks_hit_list:
                ball.change_y *= -1
                for brick in bricks_hit_list:
                    powerup = brick.hit()
                    if powerup:
                        self.powerups.append(powerup)
                        self.all_sprites.append(powerup)
        self.paddle.on_update()
        if len(self.bricks) == 0:
            self.next_level()
        if len(self.balls) == 0:
            print('>> Game over')
            arcade.close_window()
        self.powerups.update()
        for powerup in self.powerups:
            if arcade.check_for_collision(self.paddle, powerup):
                self.activate_powerup(powerup)
                powerup.remove_from_sprite_lists()
        for ball in self.balls:
            if self.paddle.collides_with_sprite(ball):
                self.paddle.check_collision_with_ball(ball)
                if ball.should_stick:
                    ball.should_stick = False
                    ball.stuck = True
                    ball.change_x = 0
                    ball.change_y = 0
                    ball.attached_to_paddle = True
                    ball.stick_to_paddle(self.paddle)

    def on_draw(self):
        self.clear()
        self.background.draw()
        self.all_sprites.draw()
        # Display level number
        arcade.draw_text(f"Level {self.level_index + 1}", WIDTH / 2, HEIGHT - 30,
                         arcade.color.WHITE, font_size=24, anchor_x="center")

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.LEFT:
            self.paddle.change_x = -1
        if symbol == arcade.key.RIGHT:
            self.paddle.change_x = 1
        if symbol == arcade.key.SPACE:
            for ball in self.balls:
                if ball.stuck:
                    ball.start_moving()
        if symbol == arcade.key.ENTER:  # Go to next level when pressing Enter
            self.next_level()

    def on_key_release(self, symbol, modifiers):
        if symbol == arcade.key.LEFT:
            self.paddle.change_x = 0
        if symbol == arcade.key.RIGHT:
            self.paddle.change_x = 0

    def activate_powerup(self, powerup):
        end_time = time.time() + powerup.duration
        self.active_powerups.append({'type': powerup.type, 'end_time': end_time})
        if powerup.type == 'green':
            for ball in self.balls:
                if not ball.should_stick and not ball.stuck:
                    ball.should_stick = True
                    break
        elif powerup.type == 'white':
            new_balls = arcade.SpriteList()
            for ball in self.balls:
                ball_copy_1 = Ball(start_attached=False, change_x=ball.change_x, change_y=ball.change_y,
                                   speed=ball.speed)
                ball_copy_1.center_x = ball.center_x
                ball_copy_2 = Ball(start_attached=False, change_x=-ball.change_x, change_y=ball.change_y,
                                   speed=ball.speed)
                ball_copy_2.center_x = ball.center_x
                ball_copy_2.center_y = ball.center_y
                new_balls.append(ball_copy_1)
                new_balls.append(ball_copy_2)
            self.balls.extend(new_balls)
            self.all_sprites.extend(new_balls)
        elif powerup.type == 'red':
            for ball in self.balls:
                ball.speed = min(ball.speed * 1.5, 21)
        elif powerup.type == 'yellow':
            for ball in self.balls:
                ball.speed = max(ball.speed / 1.3, 3.5)
        elif powerup.type == 'size':
            self.paddle.scale_factor = min(float(self.paddle.scale_factor) * 1.5, self.paddle.original_scale * 2)
            self.paddle.scale = self.paddle.scale_factor  # Apply actual scaling
        elif powerup.type == 'unsize':
            self.paddle.scale_factor = max(float(self.paddle.scale_factor) / 1.3, self.paddle.original_scale / 1.6)
            self.paddle.scale = self.paddle.scale_factor  # Apply actual scaling
        # Start timer to cancel powerup effect
        if powerup.type in ['red', 'yellow', 'size', 'unsize']:
            self.schedule_timer(powerup.type, end_time)

    def schedule_timer(self, powerup_type, end_time):
        def remove_powerup_effect():
            if powerup_type == 'red':
                for ball in self.balls:
                    ball.speed = ball.speed / 1.5
            elif powerup_type == 'yellow':
                for ball in self.balls:
                    ball.speed = ball.speed * 1.3
            elif powerup_type == 'size':
                self.paddle.scale_factor = self.paddle.original_scale
                self.paddle.scale = self.paddle.original_scale
            elif powerup_type == 'unsize':
                self.paddle.scale_factor = self.paddle.original_scale
                self.paddle.scale = self.paddle.original_scale

        arcade.schedule(lambda delta_time: remove_powerup_effect(), max(0, end_time - time.time()))


window = Arkanoid()
arcade.run()
