#!/usr/bin/env python3
import curses
import math
import time
import random

# Enhanced map with architectural elements
# '#' is a wall, '.' is empty space, 'L' is a lower wall
# 'P' is a pillar, 'C' is a corner decoration, 'D' is a door
MAP = [
    "########################################",
    "#......................................#",
    "#...###LLL#............................#",
    "#...#C...#............................P#",
    "#...#....D.........................#####",
    "#...######...........................###",
    "#....P...P............................##",
    "#....####...........................####",
    "#....#..#.............................##",
    "#....#C.#....###......................##",
    "#....####....#C#......................##",
    "#............###.....................###",
    "#...P................................P##",
    "#...#...#...#...#.....................##",
    "#......................................#",
    "########################################"
]

# Enemy positions [x, y, alive, type]
# Type: 0 = normal, 1 = fast, 2 = strong
ENEMIES = [
    [5, 3, True, 0],
    [10, 5, True, 0],
    [8, 8, True, 1],
    [15, 7, True, 0],
    [12, 10, True, 2],
    [18, 8, True, 1],
    [20, 12, True, 0]
]

FOV = 70   # Field of view in degrees
DEPTH = 16 # Maximum rendering depth

def distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def main(stdscr):
    # Print message before starting
    stdscr.clear()
    stdscr.addstr(0, 0, "Press F11 to maximize your terminal for best experience")
    stdscr.addstr(1, 0, "Press any key to start...")
    stdscr.refresh()
    stdscr.getch()  # Wait for a key

    # Curses initial settings
    curses.curs_set(0)          # Hide the cursor
    stdscr.nodelay(True)        # Non-blocking input
    stdscr.timeout(33)          # 30 FPS refresh rate

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)     # NS walls
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)      # Sky
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)     # Floor
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)       # Normal enemies
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)    # Weapon
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)      # HUD
        curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)   # Special enemies
        curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)      # Radar border
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)     # Lower walls
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_YELLOW)   # Pillar
        curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_WHITE)   # Corner
        curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_RED)      # EW walls

    # Use the full terminal size
    height, width = stdscr.getmaxyx()

    # Calculate vertical space for view (accounting for HUD)
    view_height = height - 2  # 1 for HUD at top, 1 for controls at bottom

    # Player starting state
    player_x, player_y = 2.0, 2.0
    player_height = 0.5         # Player height (for lower walls)
    player_angle = 0            # Facing right
    player_health = 100
    ammo = 50
    score = 0
    move_step = 0.3             # Movement speed
    turn_step = 3.0             # Turning speed in degrees

    # For FPS calculation
    frame_count = 0
    last_time = time.time()
    fps = 0

    # Initialize for muzzle flash
    shooting = False
    shot_timer = 0

    # Animation frame for enemies
    enemy_animation_frame = 0
    animation_timer = 0

    # Define wall textures
    ns_wall_textures = ['│', '║', '┃', '┋', '┇', '╎', '╏', '┆']  # For North-South walls
    ew_wall_textures = ['─', '═', '━', '┅', '┉', '╌', '╍', '┄']  # For East-West walls
    pillar_textures = ['╬', '╪', '╫', '╋', '╂', '┼', '╉', '╊']   # For pillars
    corner_textures = ['╔', '╗', '╚', '╝', '┌', '┐', '└', '┘']   # For corners

    # Game loop
    running = True
    while running:
        # Calculate delta time for smooth animation
        current_time = time.time()
        delta_time = current_time - last_time
        last_time = current_time

        # Calculate FPS
        frame_count += 1
        if frame_count >= 30:
            fps = frame_count / (current_time - (current_time - delta_time * frame_count))
            frame_count = 0

        # Handle enemy animation timing
        animation_timer += 1
        if animation_timer >= 8:  # Change animation every ~267ms
            enemy_animation_frame = (enemy_animation_frame + 1) % 3
            animation_timer = 0

        # Get key input (non-blocking)
        key = stdscr.getch()

        # Process movement based on key input
        if key != -1:
            if key == ord('x'):
                running = False
            elif key == ord('w'):
                new_x = player_x + math.cos(math.radians(player_angle)) * move_step
                new_y = player_y + math.sin(math.radians(player_angle)) * move_step
                if 0 <= int(new_y) < len(MAP) and 0 <= int(new_x) < len(MAP[0]) and MAP[int(new_y)][int(new_x)] not in ['#', 'P']:
                    player_x, player_y = new_x, new_y
            elif key == ord('s'):
                new_x = player_x - math.cos(math.radians(player_angle)) * move_step
                new_y = player_y - math.sin(math.radians(player_angle)) * move_step
                if 0 <= int(new_y) < len(MAP) and 0 <= int(new_x) < len(MAP[0]) and MAP[int(new_y)][int(new_x)] not in ['#', 'P']:
                    player_x, player_y = new_x, new_y
            elif key == ord('a'):
                strafe_angle = player_angle - 90
                new_x = player_x + math.cos(math.radians(strafe_angle)) * move_step
                new_y = player_y + math.sin(math.radians(strafe_angle)) * move_step
                if 0 <= int(new_y) < len(MAP) and 0 <= int(new_x) < len(MAP[0]) and MAP[int(new_y)][int(new_x)] not in ['#', 'P']:
                    player_x, player_y = new_x, new_y
            elif key == ord('d'):
                strafe_angle = player_angle + 90
                new_x = player_x + math.cos(math.radians(strafe_angle)) * move_step
                new_y = player_y + math.sin(math.radians(strafe_angle)) * move_step
                if 0 <= int(new_y) < len(MAP) and 0 <= int(new_x) < len(MAP[0]) and MAP[int(new_y)][int(new_x)] not in ['#', 'P']:
                    player_x, player_y = new_x, new_y
            elif key == ord('q'):
                player_angle = (player_angle - turn_step) % 360
            elif key == ord('e'):
                player_angle = (player_angle + turn_step) % 360
            elif key == ord(' '):
                if ammo > 0:
                    ammo -= 1
                    shooting = True
                    shot_timer = 0

                    # Check for enemy hits
                    for enemy in ENEMIES:
                        if enemy[2]:
                            dist = distance(player_x, player_y, enemy[0], enemy[1])
                            angle_to_enemy = math.degrees(math.atan2(enemy[1] - player_y, enemy[0] - player_x))
                            angle_diff = (angle_to_enemy - player_angle + 180) % 360 - 180

                            if abs(angle_diff) < FOV / 2 and dist < DEPTH:
                                hit_chance = 1.0 - (dist / DEPTH) * 0.8
                                hit_chance *= 1.0 if enemy[3] == 0 else (0.7 if enemy[3] == 1 else 0.5)  # Harder to hit faster/stronger enemies
                                if random.random() < hit_chance:
                                    enemy[2] = False
                                    score += 100 * (enemy[3] + 1)  # More points for tougher enemies
                                    break

        # Clear the screen
        stdscr.clear()

        # Get the terminal size again in case it was resized
        height, width = stdscr.getmaxyx()
        view_height = height - 2

        # --- Render the scene using raycasting ---
        for x in range(min(width, 1000)):  # Limit max width to prevent issues
            # Calculate ray angle for this column
            ray_angle = (player_angle - FOV / 2) + (x / min(width, 1000) * FOV)
            ray_angle_rad = math.radians(ray_angle)

            # Apply fisheye correction factor
            corrected_angle = ray_angle - player_angle
            fisheye_correction = math.cos(math.radians(corrected_angle))

            ray_x, ray_y = player_x, player_y
            step_size = 0.02  # Very small step size for accurate walls
            distance_to_wall = 0.0
            hit_wall = False
            hit_lower_wall = False
            hit_pillar = False
            hit_corner = False
            boundary = False  # For edge detection
            wall_orientation = 0  # 0 for vertical (NS), 1 for horizontal (EW)

            # Detect adjacent walls for corner detection
            adjacent_walls = []

            # Cast ray
            while not hit_wall and distance_to_wall < DEPTH:
                distance_to_wall += step_size
                ray_x = player_x + math.cos(ray_angle_rad) * distance_to_wall
                ray_y = player_y + math.sin(ray_angle_rad) * distance_to_wall

                # Check if out of bounds
                map_x = int(ray_x)
                map_y = int(ray_y)

                if map_x < 0 or map_y < 0 or map_x >= len(MAP[0]) or map_y >= len(MAP):
                    hit_wall = True
                    distance_to_wall = DEPTH
                elif MAP[map_y][map_x] == '#':
                    hit_wall = True

                    # Determine if hit vertical or horizontal wall side
                    test_x = ray_x - map_x
                    test_y = ray_y - map_y

                    # Test which side of the wall we hit
                    if test_x < 0.02:
                        wall_orientation = 0  # West face
                    elif test_x > 0.98:
                        wall_orientation = 0  # East face
                    elif test_y < 0.02:
                        wall_orientation = 1  # North face
                    elif test_y > 0.98:
                        wall_orientation = 1  # South face

                    # Check for wall edges for enhanced rendering
                    if test_x < 0.02 or test_x > 0.98 or test_y < 0.02 or test_y > 0.98:
                        boundary = True

                    # Check for corners by detecting adjacent walls
                    adjacent_count = 0
                    for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                        nx, ny = map_x + dx, map_y + dy
                        if 0 <= ny < len(MAP) and 0 <= nx < len(MAP[0]):
                            if MAP[ny][nx] == '#':
                                adjacent_count += 1
                                adjacent_walls.append((dx, dy))

                    if adjacent_count >= 3:  # It's likely a corner or junction
                        hit_corner = True

                elif MAP[map_y][map_x] == 'L':  # Lower wall
                    hit_lower_wall = True
                    hit_wall = True

                    # Same orientation detection as regular walls
                    test_x = ray_x - map_x
                    test_y = ray_y - map_y

                    if test_x < 0.02:
                        wall_orientation = 0  # West face
                    elif test_x > 0.98:
                        wall_orientation = 0  # East face
                    elif test_y < 0.02:
                        wall_orientation = 1  # North face
                    elif test_y > 0.98:
                        wall_orientation = 1  # South face

                    if test_x < 0.02 or test_x > 0.98 or test_y < 0.02 or test_y > 0.98:
                        boundary = True

                elif MAP[map_y][map_x] == 'P':  # Pillar
                    hit_pillar = True
                    hit_wall = True

                    # Pillars are always full-height
                    boundary = True  # Always show edges for pillars

                elif MAP[map_y][map_x] == 'C':  # Corner decoration
                    hit_corner = True
                    hit_wall = True
                    boundary = True

            # Apply fisheye correction
            corrected_distance = distance_to_wall * fisheye_correction

            # Calculate ceiling and floor positions
            if hit_lower_wall:
                # Lower walls appear shorter (only half height)
                ceiling = int(view_height / 2.0 - (view_height / corrected_distance) * 0.5)
                floor = int(view_height / 2.0 + (view_height / corrected_distance) * 0.5)
            else:
                ceiling = int(view_height / 2.0 - view_height / corrected_distance)
                floor = int(view_height / 2.0 + view_height / corrected_distance)

            ceiling = max(0, ceiling)
            floor = min(view_height - 1, floor)

            # Check if ray hits an enemy
            enemy_hit = False
            enemy_distance = float('inf')
            enemy_type = 0
            for enemy in ENEMIES:
                if enemy[2]:  # Only for alive enemies
                    dist = distance(player_x, player_y, enemy[0], enemy[1])
                    angle_to_enemy = math.degrees(math.atan2(enemy[1] - player_y, enemy[0] - player_x))
                    angle_diff = (angle_to_enemy - ray_angle + 180) % 360 - 180

                    # Slightly wider enemy hit detection
                    if abs(angle_diff) < 3 and dist < corrected_distance and dist < enemy_distance:
                        enemy_hit = True
                        enemy_distance = dist
                        enemy_type = enemy[3]

            # Draw the vertical column for this ray
            for y in range(min(view_height, 1000)):  # Limit height too
                try:
                    if y < ceiling:
                        # Sky with gradient
                        shade = max(0, min(1, 1 - (y / ceiling))) if ceiling > 0 else 0
                        if shade > 0.8:
                            stdscr.addch(y + 1, x, '·', curses.color_pair(2))
                        elif shade > 0.5:
                            stdscr.addch(y + 1, x, ' ', curses.color_pair(2))
                        else:
                            stdscr.addch(y + 1, x, ' ', curses.color_pair(2))
                    elif y >= ceiling and y <= floor:
                        if enemy_hit:
                            # Calculate enemy height based on distance
                            enemy_height = view_height / enemy_distance
                            enemy_ceiling = int(view_height / 2.0 - enemy_height / 2)
                            enemy_floor = int(view_height / 2.0 + enemy_height / 2)

                            # Only draw enemy within its calculated height
                            if y >= enemy_ceiling and y <= enemy_floor:
                                # Different enemy types
                                if enemy_type == 0:  # Normal
                                    # Basic animation
                                    enemy_chars = ['&', '@', '&']
                                    char = enemy_chars[enemy_animation_frame]
                                    stdscr.addch(y + 1, x, char, curses.color_pair(4))
                                elif enemy_type == 1:  # Fast
                                    # More active animation
                                    enemy_chars = ['%', '$', '%']
                                    char = enemy_chars[enemy_animation_frame]
                                    stdscr.addch(y + 1, x, char, curses.color_pair(7))
                                else:  # Strong
                                    # Hulking animation
                                    enemy_chars = ['M', 'W', 'M']
                                    char = enemy_chars[enemy_animation_frame]
                                    stdscr.addch(y + 1, x, char, curses.color_pair(7) | curses.A_BOLD)
                            else:
                                # Draw wall behind enemy where the enemy doesn't fill the space
                                if hit_wall:
                                    # Wall rendering with texture based on type
                                    if hit_pillar:
                                        # Draw pillar texture
                                        texture_idx = int(corrected_distance / DEPTH * len(pillar_textures))
                                        texture_idx = min(texture_idx, len(pillar_textures) - 1)
                                        char = pillar_textures[texture_idx]
                                        stdscr.addch(y + 1, x, char, curses.color_pair(10))
                                    elif hit_corner:
                                        # Draw corner texture
                                        texture_idx = int(corrected_distance / DEPTH * len(corner_textures))
                                        texture_idx = min(texture_idx, len(corner_textures) - 1)
                                        char = corner_textures[texture_idx]
                                        stdscr.addch(y + 1, x, char, curses.color_pair(11))
                                    elif hit_lower_wall:
                                        # Lower wall
                                        if corrected_distance < DEPTH / 4:
                                            char = '█'
                                        elif corrected_distance < DEPTH / 2:
                                            char = '▓'
                                        else:
                                            char = '▒'
                                        stdscr.addch(y + 1, x, char, curses.color_pair(9))
                                    else:
                                        # Regular wall - with texture based on orientation
                                        if wall_orientation == 0:  # NS wall
                                            texture_idx = int(corrected_distance / DEPTH * len(ns_wall_textures))
                                            texture_idx = min(texture_idx, len(ns_wall_textures) - 1)
                                            char = ns_wall_textures[texture_idx]
                                            color = curses.color_pair(1) | curses.A_BOLD
                                        else:  # EW wall
                                            texture_idx = int(corrected_distance / DEPTH * len(ew_wall_textures))
                                            texture_idx = min(texture_idx, len(ew_wall_textures) - 1)
                                            char = ew_wall_textures[texture_idx]
                                            color = curses.color_pair(12)

                                        stdscr.addch(y + 1, x, char, color)
                        else:
                            # Wall rendering with texture based on type
                            if hit_pillar:
                                # Draw pillar texture
                                texture_idx = int(corrected_distance / DEPTH * len(pillar_textures))
                                texture_idx = min(texture_idx, len(pillar_textures) - 1)
                                char = pillar_textures[texture_idx]
                                stdscr.addch(y + 1, x, char, curses.color_pair(10))
                            elif hit_corner:
                                # Draw corner texture
                                texture_idx = int(corrected_distance / DEPTH * len(corner_textures))
                                texture_idx = min(texture_idx, len(corner_textures) - 1)
                                char = corner_textures[texture_idx]
                                stdscr.addch(y + 1, x, char, curses.color_pair(11))
                            elif hit_lower_wall:
                                # Lower wall
                                if corrected_distance < DEPTH / 4:
                                    char = '█'
                                elif corrected_distance < DEPTH / 2:
                                    char = '▓'
                                else:
                                    char = '▒'
                                stdscr.addch(y + 1, x, char, curses.color_pair(9))
                            else:
                                # Regular wall - with texture based on orientation
                                if wall_orientation == 0:  # NS wall
                                    texture_idx = int(corrected_distance / DEPTH * len(ns_wall_textures))
                                    texture_idx = min(texture_idx, len(ns_wall_textures) - 1)
                                    char = ns_wall_textures[texture_idx]
                                    color = curses.color_pair(1) | curses.A_BOLD
                                else:  # EW wall
                                    texture_idx = int(corrected_distance / DEPTH * len(ew_wall_textures))
                                    texture_idx = min(texture_idx, len(ew_wall_textures) - 1)
                                    char = ew_wall_textures[texture_idx]
                                    color = curses.color_pair(12)

                                stdscr.addch(y + 1, x, char, color)
                    else:
                        # Floor with shading based on distance
                        b = 1.0 - ((y - floor) / max(1, view_height - floor))
                        # Enhanced floor texture with grid pattern
                        grid_size = 4  # Size of grid cells
                        grid_x = int(player_x * grid_size + math.cos(ray_angle_rad) * (y - floor) * 2) % grid_size
                        grid_y = int(player_y * grid_size + math.sin(ray_angle_rad) * (y - floor) * 2) % grid_size

                        if (grid_x == 0 or grid_y == 0) and b > 0.3:
                            # Grid lines
                            stdscr.addch(y + 1, x, '+', curses.color_pair(3))
                        elif b < 0.25:
                            stdscr.addch(y + 1, x, '#', curses.color_pair(3))
                        elif b < 0.5:
                            stdscr.addch(y + 1, x, 'x', curses.color_pair(3))
                        elif b < 0.75:
                            stdscr.addch(y + 1, x, '-', curses.color_pair(3))
                        else:
                            stdscr.addch(y + 1, x, '.', curses.color_pair(3))
                except curses.error:
                    pass  # Avoid errors when drawing at the edge

        # --- Draw weapon (ASCII art) ---
        if height > 8:  # Only draw weapon if there's enough vertical space
            # Weapon position
            weapon_y = height - 7

            # Different weapon art based on shooting status
            if shooting and shot_timer < 3:
                weapon = [
                    "    /|\\    ",
                    "   /-|-\\   ",
                    "  /--+--\\  ",
                    " /---+---\\ ",
                    "/____|____\\"
                ]
                shot_timer += 1
            else:
                weapon = [
                    "    /\\    ",
                    "   /||\\   ",
                    "  / || \\  ",
                    " /  ||  \\ ",
                    "/___||___\\"
                ]
                shooting = False
                shot_timer = 0

            # Draw the weapon
            for i, w_line in enumerate(weapon):
                if weapon_y + i < height - 1:
                    start_pos = (width - len(w_line)) // 2
                    if start_pos >= 0:
                        for j, ch in enumerate(w_line):
                            try:
                                if 0 <= start_pos + j < width:
                                    stdscr.addch(weapon_y + i, start_pos + j, ch, curses.color_pair(5))
                            except curses.error:
                                pass

        # --- Draw Enhanced Radar in the top-right corner ---
        # Calculate radar size dynamically, but keep it reasonable
        radar_size = min(15, max(10, min(width // 6, height // 4)))

        # Position in top-right corner with appropriate padding
        radar_x = max(0, width - radar_size - 2)
        radar_y = 2

        # Only draw radar if there's enough room
        if width > radar_size + 20 and height > radar_size + 6:
            # Draw radar border
            for i in range(radar_size + 2):
                try:
                    if 0 <= radar_y - 1 < height and 0 <= radar_x - 1 + i < width:
                        # Top border
                        stdscr.addch(radar_y - 1, radar_x - 1 + i, '═', curses.color_pair(8))

                    if 0 <= radar_y + radar_size < height and 0 <= radar_x - 1 + i < width:
                        # Bottom border
                        stdscr.addch(radar_y + radar_size, radar_x - 1 + i, '═', curses.color_pair(8))

                    # Left and right borders
                    if i > 0 and i < radar_size + 1:
                        if 0 <= radar_y - 1 + i < height and 0 <= radar_x - 1 < width:
                            stdscr.addch(radar_y - 1 + i, radar_x - 1, '║', curses.color_pair(8))

                        if 0 <= radar_y - 1 + i < height and 0 <= radar_x + radar_size < width:
                            stdscr.addch(radar_y - 1 + i, radar_x + radar_size, '║', curses.color_pair(8))
                except curses.error:
                    pass

            # Draw corners
            try:
                if 0 <= radar_y - 1 < height and 0 <= radar_x - 1 < width:
                    stdscr.addch(radar_y - 1, radar_x - 1, '╔', curses.color_pair(8))

                if 0 <= radar_y - 1 < height and 0 <= radar_x + radar_size < width:
                    stdscr.addch(radar_y - 1, radar_x + radar_size, '╗', curses.color_pair(8))

                if 0 <= radar_y + radar_size < height and 0 <= radar_x - 1 < width:
                    stdscr.addch(radar_y + radar_size, radar_x - 1, '╚', curses.color_pair(8))

                if 0 <= radar_y + radar_size < height and 0 <= radar_x + radar_size < width:
                    stdscr.addch(radar_y + radar_size, radar_x + radar_size, '╝', curses.color_pair(8))
            except curses.error:
                pass

            # Add label to radar
            try:
                radar_label = " RADAR "
                label_pos = radar_x + (radar_size - len(radar_label)) // 2
                if 0 <= radar_y - 1 < height and 0 <= label_pos < width and label_pos + len(radar_label) <= width:
                    stdscr.addstr(radar_y - 1, label_pos, radar_label, curses.color_pair(8) | curses.A_BOLD)
            except curses.error:
                pass

            # Calculate visible area size
            # We want to show more of the map, so we'll use a larger scale
            scale = 1.0
            visible_range = radar_size / scale  # How much of the map fits in the radar

            # Draw the map on the radar
            for y in range(radar_size):
                for x in range(radar_size):
                    # Only proceed if within bounds
                    if 0 <= radar_y + y < height and 0 <= radar_x + x < width:
                        # Calculate real map coordinates
                        map_x_pos = int(player_x - visible_range/2 + x / scale)
                        map_y_pos = int(player_y - visible_range/2 + y / scale)

                        try:
                            if 0 <= map_y_pos < len(MAP) and 0 <= map_x_pos < len(MAP[0]):
                                if map_x_pos == int(player_x) and map_y_pos == int(player_y):
                                    # Player with direction indicator
                                    dir_char = '▲'  # Default up
                                    if 45 <= player_angle < 135:
                                        dir_char = '▶'  # Right
                                    elif 135 <= player_angle < 225:
                                        dir_char = '▼'  # Down
                                    elif 225 <= player_angle < 315:
                                        dir_char = '◀'  # Left
                                    stdscr.addch(radar_y + y, radar_x + x, dir_char, curses.color_pair(5) | curses.A_BOLD)
                                elif MAP[map_y_pos][map_x_pos] == '#':
                                    stdscr.addch(radar_y + y, radar_x + x, '■', curses.color_pair(1))
                                elif MAP[map_y_pos][map_x_pos] == 'L':
                                    stdscr.addch(radar_y + y, radar_x + x, '□', curses.color_pair(9))
                                elif MAP[map_y_pos][map_x_pos] == 'P':
                                    stdscr.addch(radar_y + y, radar_x + x, '◘', curses.color_pair(10))
                                elif MAP[map_y_pos][map_x_pos] == 'C':
                                    stdscr.addch(radar_y + y, radar_x + x, '◙', curses.color_pair(11))
                                else:
                                    stdscr.addch(radar_y + y, radar_x + x, '·', curses.color_pair(6))

                                # Draw enemies on map with different symbols based on type
                                for enemy in ENEMIES:
                                    if enemy[2] and int(enemy[0]) == map_x_pos and int(enemy[1]) == map_y_pos:
                                        if enemy[3] == 0:  # Normal
                                            stdscr.addch(radar_y + y, radar_x + x, '○', curses.color_pair(4) | curses.A_BOLD)
                                        elif enemy[3] == 1:  # Fast
                                            stdscr.addch(radar_y + y, radar_x + x, '◇', curses.color_pair(7) | curses.A_BOLD)
                                        else:  # Strong
                                            stdscr.addch(radar_y + y, radar_x + x, '◆', curses.color_pair(7) | curses.A_BOLD)
                        except (curses.error, IndexError):
                            pass

        # --- Draw HUD with stats ---
        try:
            hud_str = f"Health: {player_health}  Ammo: {ammo}  Score: {score}  FPS: {int(fps)}"
            if 0 <= 0 < height and 0 <= 2 < width and 2 + len(hud_str) <= width:
                stdscr.addstr(0, 2, hud_str, curses.color_pair(6))

            # Add position info only if there's room
            if width > 60:
                pos_str = f"Pos: ({player_x:.1f},{player_y:.1f}) Angle: {player_angle:.0f}°"
                pos_x = min(len(hud_str) + 5, width - len(pos_str) - 2)
                if 0 <= 0 < height and 0 <= pos_x < width and pos_x + len(pos_str) <= width:
                    stdscr.addstr(0, pos_x, pos_str, curses.color_pair(6))
        except curses.error:
            pass

        # --- Draw controls info ---
        try:
            controls = "WASD: Move | Q/E: Turn | Space: Shoot | X: Exit"
            controls_x = (width - len(controls)) // 2
            if controls_x < 0:
                controls_x = 0
            if controls_x + len(controls) > width:
                controls = controls[:width - controls_x]

            if 0 <= height - 1 < height and 0 <= controls_x < width:
                stdscr.addstr(height - 1, controls_x, controls, curses.color_pair(6))
        except curses.error:
            pass

        # Refresh the screen
        stdscr.refresh()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"Error: {e}")
