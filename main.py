from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random # Ensure random is imported
from math import radians, cos, sin, sqrt, atan2 # Import necessary math functions, including sqrt and atan2 for safety although often pulled in by ursina

# Initialize the Ursina application
app = Ursina()

# Add a ground plane
ground = Entity(model='plane', scale=(100, 1, 100), color=color.rgb(20, 20, 100), texture='white_cube', texture_scale=(100, 100), collider='box')

# Add a first-person controller (Mymy)
player = FirstPersonController(y=2, origin_y=-.5, speed=5, jump_height=2.5, gravity=0.8) # Adjusted jump_height and gravity
player.gun = None # We can add a gun model later
player.health = 100
player.max_health = 100
player.external_velocity = Vec3(0,0,0) # For knockback
player.mass_factor = 1.0 # Higher = less knockback
player_drag_factor = 1.0 # How quickly player's external velocity decays
normal_speed = 5
sprint_speed = 8

# Weapon properties
WEAPON_HITSCAN = 'hitscan'
WEAPON_ROCKET_LAUNCHER = 'rocket_launcher'
available_weapons = [WEAPON_HITSCAN, WEAPON_ROCKET_LAUNCHER]
current_weapon_index = 0
player.current_weapon = available_weapons[current_weapon_index]

# HUD Elements
health_text = Text(text=f"Health: {player.health}", parent=camera.ui, origin=(-.5, .5), position=(-0.85, 0.45), scale=1.5, color=color.green)
# Minimap / Radar
minimap_size = 0.2
minimap_pos = (-0.88, -0.38) # Bottom left corner
minimap_background = Entity(parent=camera.ui, model='quad', color=color.rgba(0,0,0,100), scale=minimap_size, position=minimap_pos)
minimap_player_dot = Entity(parent=minimap_background, model='circle', color=color.cyan, scale=0.05) # Player is always center
radar_range = 50 # World units range for radar
enemy_dots = []


# Add a sky
Sky()

# Weapon Placeholders
gun_model = Entity(parent=camera, model='cube', color=color.gray, scale=(0.1, 0.1, 0.3), position=(0.3, -0.2, 0.5), rotation=(-5, 10, -5), visible=False)
rocket_launcher_model = Entity(parent=camera, model='cylinder', color=color.dark_gray, scale=(0.15, 0.3, 0.15), position=(0.3, -0.2, 0.5), rotation=(0, 10, -5), visible=False)

# Function to update weapon model visibility
def update_weapon_model():
    if player.current_weapon == WEAPON_HITSCAN:
        gun_model.visible = True
        rocket_launcher_model.visible = False
    elif player.current_weapon == WEAPON_ROCKET_LAUNCHER:
        gun_model.visible = False
        rocket_launcher_model.visible = True
    else:
        gun_model.visible = False
        rocket_launcher_model.visible = False

# Camera bobbing parameters
bob_frequency = 10
bob_amplitude_x = 0.03
bob_amplitude_y = 0.04
bob_timer = 0
# Store the original camera pivot y offset, FPC might reset it
original_camera_pivot_y = player.camera_pivot.y

def update():
    global bob_timer
    # Camera Bobbing
    # is_moving = player.moving # Incorrect: FPC may not have 'moving' attribute or it might not behave as expected for this.
    # Check if any movement keys are pressed (W, A, S, D)
    is_moving = held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']

    if is_moving and player.grounded: # Bob only when moving and grounded
        bob_timer += time.dt * bob_frequency
        # Apply bob to the camera_pivot, which the actual camera follows
        player.camera_pivot.x = sin(bob_timer) * bob_amplitude_x
        # Add to original y, don't replace, to respect FPC's height settings
        player.camera_pivot.y = original_camera_pivot_y + cos(bob_timer / 2) * bob_amplitude_y
    else:
        bob_timer = 0
        # Smoothly reset camera_pivot offsets
        player.camera_pivot.x = lerp(player.camera_pivot.x, 0, time.dt * 10)
        player.camera_pivot.y = lerp(player.camera_pivot.y, original_camera_pivot_y, time.dt * 10)

    # Update health text color based on health percentage
    health_percentage = player.health / player.max_health if player.max_health > 0 else 0 # Avoid division by zero

    # Apply and dampen player's external velocity
    # The FirstPersonController might override direct position changes, especially Y due to gravity.
    # We'll try to influence its existing movement.
    # For XZ movement from knockback:
    if player.external_velocity.length_squared() > 0.01:
        # This is tricky because FPC calculates its own movement.
        # A simple way is to add to player's position, but FPC might clamp/override.
        # Let's try adding to controller's current direction temporarily if possible, or just add to position.
        player.x += player.external_velocity.x * time.dt
        player.z += player.external_velocity.z * time.dt
        # For Y, the FPC gravity is strong. The jump_height hack in fire_rocket is the primary way for upward.
        # If player is in air due to knockback, FPC gravity will still act.
        player.external_velocity.x *= (1 - time.dt * player_drag_factor)
        player.external_velocity.z *= (1 - time.dt * player_drag_factor)
        if abs(player.external_velocity.x) < 0.1: player.external_velocity.x = 0
        if abs(player.external_velocity.z) < 0.1: player.external_velocity.z = 0
        # Y velocity from external forces will likely be negated quickly by FPC gravity unless very high
        player.external_velocity.y *= (1 - time.dt * player_drag_factor)
        if abs(player.external_velocity.y) < 0.1: player.external_velocity.y = 0


    if health_percentage > 0.6:
        health_text.color = color.green
    elif health_percentage > 0.3:
        health_text.color = color.orange
    else:
        health_text.color = color.red
    health_text.text = f"Health: {max(0, player.health)}" # Ensure health doesn't display below 0


def player_take_damage(amount):
    if player.health <= 0: # Already game over
        return
    player.health -= amount
    Audio('sounds/player_hurt.wav', autoplay=True, volume=0.6) # Conceptual sound
    print(f"Player took {amount} damage, health is now {player.health}")
    if player.health <= 0:
        Audio('sounds/player_die.wav', autoplay=True, volume=0.7) # Conceptual sound
        game_over()

def game_over():
    print("GAME OVER")
    Text(text="GAME OVER", origin=(0,0), scale=3, color=color.red, background=True)
    player.enabled = False # Disable player movement and input
    # Potentially show a cursor and a restart button in a real game
    # For now, just quit after a delay
    invoke(application.quit, delay=5)


# Function to handle input
def input(key):
    global current_weapon_index # Declare global to modify it
    if player.health <= 0: # Disable input if game over
        if key == 'escape': # Still allow escape to quit
            application.quit()
        return

    if key == 'escape':
        app.quit()
    if key == 'left mouse down':
        shoot()
    if key == 'left shift':
        player.speed = sprint_speed
    if key == 'left shift up':
        player.speed = normal_speed
    if key == '1':
        current_weapon_index = 0
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    if key == '2':
        current_weapon_index = 1
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    # Optional: Mouse wheel for weapon switching
    if key == 'scroll up':
        current_weapon_index = (current_weapon_index - 1 + len(available_weapons)) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    if key == 'scroll down':
        current_weapon_index = (current_weapon_index + 1) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()

# Initialize weapon model at start
update_weapon_model()

def shoot():
    print(f"Shooting {player.current_weapon}")

    # Recoil Animation
    weapon_model_to_recoil = gun_model if player.current_weapon == WEAPON_HITSCAN else rocket_launcher_model
    if weapon_model_to_recoil.visible:
        original_rotation = weapon_model_to_recoil.rotation
        recoil_amount = -10 if player.current_weapon == WEAPON_HITSCAN else -15 # Degrees upward kick for x-axis

        # Kick up
        weapon_model_to_recoil.animate_rotation_x(original_rotation.x + recoil_amount, duration=0.05, curve=curve.out_sine)
        # Return to original
        weapon_model_to_recoil.animate_rotation_x(original_rotation.x, duration=0.1, delay=0.05, curve=curve.in_out_sine) # Corrected curve name


    if player.current_weapon == WEAPON_HITSCAN:
        fire_hitscan()
    elif player.current_weapon == WEAPON_ROCKET_LAUNCHER:
        fire_rocket()

def fire_hitscan():
    # Create a small, temporary line to represent the bullet trail
    bullet_trail = Entity(
        parent=camera.ui, model='quad', color=color.yellow,
        scale=(0.05, 0.2), position=(0, 0, 0.1), rotation_z=45
    )
    bullet_trail.animate_scale((0,0), duration=0.1)
    bullet_trail.fade_out(duration=0.1) # Changed from animate_alpha
    destroy(bullet_trail, delay=0.15)

    # Muzzle flash for hitscan
    muzzle_flash_hitscan = Entity(parent=gun_model, model='sphere', color=color.yellow, scale=0.3, position=(0, 0.1, 1)) # Positioned relative to gun model's front
    muzzle_flash_hitscan.animate_scale(0, duration=0.1)
    destroy(muzzle_flash_hitscan, delay=0.1)
    Audio('sounds/gun_shoot.wav', autoplay=True, volume=0.5) # Conceptual sound

    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,])
    if hit_info.hit:
        print(f"Hitscan hit: {hit_info.entity}")
        if isinstance(hit_info.entity, Enemy): # Changed Target to Enemy
            print(f"Enemy at {hit_info.entity.position} shot with {player.current_weapon}!")
            hit_info.entity.hit()

def fire_rocket():
    print("Firing Rocket!")

    # Muzzle flash for rocket launcher
    muzzle_flash_rocket = Entity(parent=rocket_launcher_model, model='sphere', color=color.rgba(255,165,0,200), scale=0.5, position=(0, 0, 0.7)) # Positioned relative to rocket launcher model's front
    muzzle_flash_rocket.animate_scale(0, duration=0.2)
    destroy(muzzle_flash_rocket, delay=0.2)
    Audio('sounds/rocket_shoot.wav', autoplay=True, volume=0.7) # Conceptual sound

    # Simulate rocket projectile and explosion point
    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,]) # Removed thickness argument

    explosion_point = hit_info.world_point if hit_info.hit else player.camera_pivot.world_position + camera.forward * 100

    # Create a visual effect for the explosion
    explosion_effect = Entity(model='sphere', color=color.orange, scale=0.1, position=explosion_point)
    explosion_effect.animate_scale(5, duration=0.4, curve=curve.out_expo) # Larger explosion
    explosion_effect.animate_color(color.rgba(255,100,0,0), duration=0.4, delay=0.1) # Fade out
    destroy(explosion_effect, delay=0.5)
    Audio('sounds/explosion.wav', autoplay=True, volume=0.8, position=explosion_point) # Conceptual sound, 3D position

    # Apply knockback in a radius
    blast_radius = 8
    player_knockback_force = 800 # Tuned for rocket jump
    target_knockback_force = 250 # Force for targets
    rocket_damage = 100 # Damage for targets

    # --- Player Knockback (Rocket Jump) ---
    # Calculate distance from player's feet (approx) to explosion for more accurate rocket jump feel
    player_feet_pos = player.position + Vec3(0, -player.origin_y, 0)
    dist_to_player = distance(player_feet_pos, explosion_point)

    if dist_to_player < blast_radius:
        print(f"Player in blast radius: {dist_to_player}m")
        # Direction from explosion to player's feet
        direction_to_player = (player_feet_pos - explosion_point).normalized()

        # More upward component if explosion is below the player
        if explosion_point.y < player_feet_pos.y:
            direction_to_player.y = abs(direction_to_player.y) * 1.5 + 0.5 # Emphasize upward

        knockback_strength = player_knockback_force * (1 - (dist_to_player / blast_radius))

        # Apply impulse: Modify player's y position directly for jump, and xz for movement
        # Ursina's FPC doesn't have a direct 'add_force' or velocity manipulation.
        # This is a simplified impulse.
        # player.y += direction_to_player.y * knockback_strength * time.dt * 0.3 # Scaled dt factor for jump
        # player.x += direction_to_player.x * knockback_strength * time.dt * 0.2
        # player.z += direction_to_player.z * knockback_strength * time.dt * 0.2
        knockback_impulse_player = direction_to_player * (knockback_strength / player.mass_factor) * 0.02 # Multiplied by small factor to act like impulse not continuous force
        player.external_velocity += knockback_impulse_player
        # Special handling for y to ensure rocket jump works against FPC gravity
        if knockback_impulse_player.y > 0 : player.jump_height = knockback_impulse_player.y # Temporarily set jump height for FPC

        print(f"Applied knockback impulse to player: {knockback_impulse_player}")

    # --- Target Knockback and Damage ---
    # Iterate over a copy of entities if destroying them
    for e in list(scene.entities):
        if isinstance(e, Enemy) and e.enabled: # Changed Target to Enemy
            dist_to_target = distance(e.position, explosion_point)
            if dist_to_target < blast_radius:
                print(f"Enemy {e.name} in blast radius: {dist_to_target}m")

                direction_to_target = (e.position - explosion_point).normalized()
                knockback_strength_on_enemy = target_knockback_force * (1 - (dist_to_target / blast_radius))
                knockback_impulse_enemy = direction_to_target * (knockback_strength_on_enemy / e.mass_factor) * 0.02
                e.external_velocity += knockback_impulse_enemy
                print(f"Applied knockback impulse to enemy {e.name}: {knockback_impulse_enemy}")

                e.hit(damage=rocket_damage, is_explosion=True)


class Enemy(Entity): # Renamed Target to Enemy
    def __init__(self, position=(0,0,0), texture_name='brick', health=100, speed=2, attack_damage=10, attack_cooldown=1.5, mass_factor=1.0):
        super().__init__(
            parent=scene,
            model='cube',
            texture=texture_name,
            color=color.white, # Will be tinted red when aggressive
            position=position,
            collider='box'
        )
        self.health = health
        self.max_health = health
        self.speed = speed
        self.attack_damage = attack_damage
        self.attack_cooldown_timer = 0
        self.attack_cooldown_duration = attack_cooldown
        self.is_aggressive = False # Becomes aggressive when player is close
        self.external_velocity = Vec3(0,0,0)
        self.mass_factor = mass_factor
        self.drag_factor = 1.5 # How quickly knockback velocity decays

        # Behavior timers/states
        self.state = 'seeking' # 'seeking', 'strafing', 'attacking_pause'
        self.state_timer = 0
        self.strafe_direction = 1 # 1 for right, -1 for left

    def update(self):
        # Apply and dampen external velocity
        self.position += self.external_velocity * time.dt
        self.external_velocity *= (1 - time.dt * self.drag_factor)
        # Stop small velocities to prevent endless sliding
        if self.external_velocity.length_squared() < 0.01:
            self.external_velocity = Vec3(0,0,0)

        if not self.enabled or player.health <= 0:
            return

        self.attack_cooldown_timer -= time.dt

        dist_to_player = distance_xz(self.position, player.position)

        # Aggro range
        if not self.is_aggressive and dist_to_player < 20:
            self.is_aggressive = True
            self.animate_color(color.rgb(255, 100, 100), duration=0.5) # Tint red

        if self.is_aggressive:
            # Look at player (optional, makes them rotate)
            self.look_at_2d(player.position, 'y') # look_at_2d ignores y difference

            # Move towards player
            # Behavior state machine
            self.state_timer -= time.dt

            if self.state == 'attacking_pause':
                if self.state_timer <= 0:
                    self.state = 'seeking' # Resume seeking after pause

            elif self.state == 'strafing':
                if self.state_timer <= 0:
                    self.state = 'seeking'
                else:
                    # Strafe: move perpendicular to player
                    perp_direction = Vec3(player.z - self.z, 0, -(player.x - self.x)).normalized() * self.strafe_direction
                    self.position += perp_direction * self.speed * 0.75 * time.dt # Strafe slower
                    self.look_at_2d(player.position, 'y') # Keep looking at player

            elif self.state == 'seeking':
                move_direction = (player.position - self.position).normalized()
                self.position += move_direction * self.speed * time.dt
                self.look_at_2d(player.position, 'y')

                # Chance to start strafing if not too close and not cooling down from attack
                if dist_to_player > 5 and random.random() < 0.01 and self.attack_cooldown_timer <= self.attack_cooldown_duration - 0.5 : # Low chance each frame
                    self.state = 'strafing'
                    self.state_timer = random.uniform(0.5, 1.5) # Strafe for 0.5-1.5 seconds
                    self.strafe_direction = random.choice([-1, 1])
                    print(f"Enemy {self.name} starts strafing.")

            # Attack if close enough and cooldown ready (regardless of seeking/strafing state if close)
            if dist_to_player < 2.5 and self.attack_cooldown_timer <= 0: # Attack range slightly increased
                print(f"Enemy {self.name} attacks player!")
                player_take_damage(self.attack_damage)
                self.attack_cooldown_timer = self.attack_cooldown_duration
                self.state = 'attacking_pause' # Pause briefly after attacking
                self.state_timer = 0.5 # Pause for 0.5 seconds
                # Simple attack animation
                self.animate_scale(self.scale * 1.2, duration=0.1, curve=curve.out_sine)
                self.animate_scale(self.scale, duration=0.1, delay=0.1, curve=curve.in_sine)


    def hit(self, damage=50, is_explosion=False):
        self.health -= damage
        Audio('sounds/enemy_hurt.wav', autoplay=True, volume=0.4, position=self.world_position) # Conceptual sound
        print(f"Enemy {self.name} hit. Health: {self.health}/{self.max_health}")

        # Become aggressive if hit
        if not self.is_aggressive:
            self.is_aggressive = True
            self.animate_color(color.rgb(255, 100, 100), duration=0.5)


        if self.health <= 0:
            Audio('sounds/enemy_die.wav', autoplay=True, volume=0.5, position=self.world_position) # Conceptual sound
            if is_explosion:
                print(f"Enemy {self.name} at {self.position} was destroyed by an explosion!")
            else:
                print(f"Enemy {self.name} at {self.position} was destroyed by raycast!")
            destroy(self)
        else:
            self.blink(color.white, duration=0.15) # Blink white when hit
            # Chance to drop health pickup if not an explosion kill (to avoid clutter from AoE)
            if not is_explosion and random.random() < 0.25: # 25% chance
                HealthPickup(position=self.position + Vec3(0,0.5,0)) # Spawn slightly above ground


class HealthPickup(Entity):
    def __init__(self, position=(0,1,0), heal_amount=25):
        super().__init__(
            parent=scene,
            model='sphere', # Could be a cross or something more distinct
            collider='sphere',
            color=color.rgb(0, 255, 0, 200), # Bright green, slightly transparent
            position=position,
            scale=0.5
        )
        self.heal_amount = heal_amount
        self.rotation_speed = 50
        self.start_y = self.y # Store initial y for bobbing
        # Add a light glow (optional, might impact performance if many)
        # self.point_light = PointLight(parent=self, color=color.green, range=10, shadows=False)


    def update(self):
        # Make it visually distinct - bobbing and spinning
        self.rotation_y += self.rotation_speed * time.dt
        self.y = self.start_y + sin(time.time() * 2) * 0.1 # Bobbing effect

        # Check for collision with player
        if self.enabled and distance_xz(player.position, self.position) < 1.5: # Collision check radius
            if player.health < player.max_health:
                player.health = min(player.max_health, player.health + self.heal_amount)
                print(f"Player picked up health. Health: {player.health}")
                Audio('sounds/pickup_health.wav', autoplay=True, volume=0.6) # Conceptual sound
                destroy(self)
            # else: player is at max health, do nothing to the pickup


# Place some enemies in the scene (formerly targets)
enemy1 = Enemy(position=(0, 1, 20), texture_name='shore', health=100, speed=2.5)
enemy2 = Enemy(position=(-10, 1, 25), texture_name='grass', health=150, speed=1.5)
enemy3 = Enemy(position=(10, 1, 15), health=100, speed=2)
# Note: Enemies should spawn at y=1 (or their height/2) if ground is at y=0 for them to be on the ground.
# FirstPersonController origin is at its base, so player.y=2 means player base is on ground if ground is at 0.
# Entities origin is center by default, so y=1 for a cube of scale 1 means its base is at y=0.5. Adjusted y for enemies.

# Wave Management
current_wave_number = 0
enemies_in_scene = []
wave_hud_text = Text(text=f"Wave: {current_wave_number}", parent=camera.ui, origin=(.5, .5), position=(0.85, 0.45), scale=1.5, color=color.white)

def start_next_wave():
    global current_wave_number, enemies_in_scene
    current_wave_number += 1
    wave_hud_text.text = f"Wave: {current_wave_number}"
    print(f"Starting Wave {current_wave_number}")

    # Clear any old references if any (should be destroyed already)
    enemies_in_scene = [e for e in enemies_in_scene if e.enabled]

    num_enemies_to_spawn = current_wave_number * 2 # Example: 2 enemies for wave 1, 4 for wave 2
    for i in range(num_enemies_to_spawn):
        # Spawn enemies at random positions around the player, but not too close
        angle = random.uniform(0, 360)
        radius = random.uniform(15, 30)
        spawn_x = player.x + cos(radians(angle)) * radius
        spawn_z = player.z + sin(radians(angle)) * radius

        # Vary enemy stats slightly per wave or per enemy
        enemy_health = 100 + (current_wave_number * 10)
        enemy_speed = 2 + (current_wave_number * 0.1)

        new_enemy = Enemy(
            position=(spawn_x, 1, spawn_z),
            texture_name='brick' if i % 2 == 0 else 'grass', # Alternate textures
            health=enemy_health,
            speed=enemy_speed
        )
        enemies_in_scene.append(new_enemy)

    # Initial placeholder enemies (enemy1, enemy2, enemy3) should be removed if using wave system from start
    # For now, let's assume they are part of "wave 0" or pre-placed and the system starts after them.
    # Or, better, disable them and start wave 1 immediately.
    if 'enemy1' in globals() and enemy1.enabled: enemy1.disable()
    if 'enemy2' in globals() and enemy2.enabled: enemy2.disable()
    if 'enemy3' in globals() and enemy3.enabled: enemy3.disable()


def check_wave_completion():
    global enemies_in_scene
    # Filter out destroyed enemies
    enemies_in_scene = [e for e in enemies_in_scene if e.enabled]
    if not enemies_in_scene and player.health > 0: # All enemies defeated
        print("Wave complete!")
        start_next_wave()

# Modify update to check for wave completion
_original_update = update # Store original update
def update(): # Override update
    _original_update() # Call original camera bobbing and health text update
    if player.health > 0: # Only check wave completion if player is alive
        check_wave_completion()

    update_radar()


def update_radar():
    global enemy_dots
    # Clear old dots
    for dot in enemy_dots:
        destroy(dot)
    enemy_dots.clear()

    if not hasattr(player, 'camera_pivot'): # Ensure player camera pivot exists
        return

    for enemy in enemies_in_scene:
        if not enemy.enabled:
            continue

        # Vector from player to enemy
        vec_to_enemy = enemy.world_position - player.world_position
        dist_to_enemy = vec_to_enemy.length()

        if dist_to_enemy < radar_range:
            # Rotate the vector by the inverse of the player's y-rotation to make it player-relative
            # Player's forward is along their local z-axis. Camera forward is what we usually care about for view.
            # For a top-down radar, we care about player's world rotation around Y.

            # Project onto XZ plane for radar
            diff_xz = vec_to_enemy.xz

            # Player's local coordinate system (on XZ plane)
            # Forward is where the camera is looking, projected onto XZ
            player_fwd_radar = player.forward.xz.normalized()
            # Right is perpendicular to forward on XZ plane
            player_right_radar = Vec2(player_fwd_radar.y, -player_fwd_radar.x) # Effectively camera.right.xz.normalized() but derived simply

            # Transform enemy diff vector to player's local radar coordinates
            # dot_x is projection onto player's right, dot_y is projection onto player's forward
            dot_x_local = diff_xz.dot(player_right_radar)
            dot_y_local = diff_xz.dot(player_fwd_radar)

            # Scale to minimap size
            map_scale = (minimap_size / 2) / radar_range # How much one world unit scales to map units

            dot_x_on_map = dot_x_local * map_scale
            dot_y_on_map = dot_y_local * map_scale

            # Clamp dots to be within the minimap circle
            dist_on_map_sq = dot_x_on_map**2 + dot_y_on_map**2
            max_dist_on_map_sq = (minimap_size / 2.05)**2 # Using 2.05 to keep dots slightly inside border

            if dist_on_map_sq > max_dist_on_map_sq:
                dist_on_map_val = sqrt(dist_on_map_sq)
                dot_x_on_map = (dot_x_on_map / dist_on_map_val) * (minimap_size / 2.05)
                dot_y_on_map = (dot_y_on_map / dist_on_map_val) * (minimap_size / 2.05)

            dot = Entity(parent=minimap_background, model='circle', color=color.red, scale=0.03, position=(dot_x_on_map, dot_y_on_map, -0.1))
            enemy_dots.append(dot)


# Add simple instructions
instructions = dedent('''
    <scale:1.5><black>Controls:
    WASD to move
    Mouse to look
    Left Click to shoot (1: Gun, 2: Rocket)
    Shift to Sprint
    ESC to quit
''').strip()

Text(text=instructions, origin=(-.5, .5), position=(-0.65, 0.4), scale=1.2, background=True, color=color.black)

# Start the first wave
start_next_wave()

# Start the game
app.run()
